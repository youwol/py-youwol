import base64
import itertools
import os
import shutil
import uuid
from pathlib import Path
from typing import Union, Mapping

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from .configurations import Configuration, get_configuration
from .models import (
    Projects, ProjectSnippet, Project, NewProjectResponse, NewProject, Workflow,
    BuilderRendering, RunnerRendering, Requirements, LoadingGraph, UploadResponse, EditMetadata, Component,
    )

from .utils import (
    init_resources, Constants, create_tmp_folder, extract_zip_file, retrieve_project, update_project,
    create_project_from_json, update_metadata, update_component, retrieve_component,
    )
from youwol_utils import (
    User, Request, user_info, get_all_individual_groups, Group, private_group_id, to_group_id,
    generate_headers_downstream, asyncio, chunks, check_permission_or_raise, RecordsResponse, GetRecordsBody,
    RecordsTable, RecordsKeyspace, RecordsBucket, RecordsDocDb, RecordsStorage, get_group, Query, QueryBody,
    )

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "flux-backend serving"}


@router.get(
    "/user-info",
    response_model=User,
    summary="retrieve user info")
async def get_user_info(request: Request):

    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    groups = [Group(id=private_group_id(user), path="private")] + \
             [Group(id=str(to_group_id(g)), path=g) for g in groups if g]

    return User(name=user['preferred_username'], groups=groups)


@router.get("/projects",
            response_model=Projects,
            summary="retrieve the list of projects")
async def list_projects(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    requests = [doc_db.query(query_body=QueryBody(query=Query()), owner=group, headers=headers)
                for group in groups]
    projects = await asyncio.gather(*requests)
    flatten_groups = list(flatten([len(project["documents"])*[groups[i]] for i, project in enumerate(projects)]))
    flatten_projects = list(flatten([project["documents"] for project in projects]))

    snippets = [ProjectSnippet(name=r["name"], id=r["project_id"], description=r["description"],
                               fluxPacks=r["packages"])
                for r, group in zip(flatten_projects, flatten_groups)]

    return Projects(projects=snippets)


@router.delete("/projects",
               response_model=Projects,
               summary="delete all the projects")
async def delete_projects(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
        ):

    await asyncio.gather(configuration.doc_db.delete_table(), configuration.storage.delete_bucket(force_not_empty=True))
    await init_resources(configuration)

    return await list_projects(request)


@router.get("/projects/{project_id}",
            response_model=Project,
            summary="retrieve a project")
async def get_project(
        request: Request,
        project_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    owner = configuration.default_owner

    project = await retrieve_project(project_id=project_id, owner=owner, storage=configuration.storage,
                                     docdb=configuration.doc_db, headers=headers)

    return project


@router.post("/projects/create",
             summary="create a new project",
             response_model=NewProjectResponse)
async def new_project(
        request: Request,
        project_body: NewProject,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)

    project_id = str(uuid.uuid4())
    workflow = Workflow(modules=[], connections=[], rootLayerTree=Constants.wf_root_layer)
    builder_rendering = BuilderRendering(modulesView=[], connectionsView=[], descriptionsBoxes=[])
    runner_rendering = RunnerRendering(layout="", style="")
    requirements = Requirements(fluxPacks=[], fluxComponents=[],
                                libraries=[],
                                loadingGraph=LoadingGraph(graphType="sequential-v1", lock=[], definition=[[]]))

    project = Project(name=project_body.name, description=project_body.description, workflow=workflow,
                      builderRendering=builder_rendering, runnerRendering=runner_rendering, requirements=requirements)

    coroutines = update_project(project_id=project_id, owner=configuration.default_owner, project=project,
                                storage=configuration.storage, docdb=configuration.doc_db, headers=headers)
    await asyncio.gather(*coroutines)
    return NewProjectResponse(projectId=project_id, libraries=requirements.libraries)


@router.post("/projects/{project_id}/duplicate",
             summary="duplicate a project",
             response_model=NewProjectResponse)
async def duplicate(
        request: Request,
        project_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    owner = configuration.default_owner
    project = await retrieve_project(
        project_id=project_id, owner=owner, storage=configuration.storage,  docdb=configuration.doc_db,
        headers=headers)

    project_id = str(uuid.uuid4())

    coroutines = update_project(project_id=project_id, project=project, owner=owner, storage=configuration.storage,
                                docdb=configuration.doc_db, headers=headers)
    await asyncio.gather(*coroutines)

    return NewProjectResponse(projectId=project_id, libraries=project.requirements.libraries)


@router.post("/projects/upload", summary="upload projects")
async def upload(
        request: Request,
        file: UploadFile = File(...),
        configuration: Configuration = Depends(get_configuration)):

    dir_path, zip_path, zip_dir_name = create_tmp_folder(file.filename)
    headers = generate_headers_downstream(request.headers)

    try:
        compressed_size, _ = extract_zip_file(file, zip_path, dir_path)
        projects_folder = flatten([[Path(root) for f in files if f == "workflow.json"]
                                   for root, _, files in os.walk(dir_path / zip_dir_name)])
        projects_folder = list(projects_folder)
        projects = [create_project_from_json(folder) for folder in projects_folder]

        coroutines = [update_project(project_id=pid, owner=configuration.default_owner, project=project,
                                     storage=configuration.storage, docdb=configuration.doc_db, headers=headers)
                      for pid, project in projects]

        coroutines_flat = flatten(coroutines)
        for chunk in chunks(coroutines_flat, 25):
            await asyncio.gather(*chunk)

        return UploadResponse(project_ids=[pid for pid, _ in projects])
    finally:
        shutil.rmtree(dir_path)


@router.delete("/projects/{project_id}", summary="delete a project")
async def delete_project(
        request: Request,
        project_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    group = await get_group("project_id", project_id, groups, doc_db, headers)

    if group == -1:
        raise HTTPException(status_code=404, detail="delete_project: project not found")

    check_permission_or_raise(group, user["memberof"])

    base_path = f"projects/{project_id}"
    storage = configuration.storage
    await doc_db.delete_document(doc={"project_id": project_id}, owner=group, headers=headers)
    await storage.delete_group(prefix=base_path, owner=group, headers=headers)

    return {"status": "deleted", "projectId": project_id}


@router.post("/projects/{project_id}/metadata", summary="edit metadata of a project")
async def post_metadata(
        request: Request,
        project_id: str,
        metadata_body: EditMetadata,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    doc_db, storage, cdn = configuration.doc_db, configuration.storage, configuration.cdn_client
    owner = configuration.default_owner

    req, workflow = await asyncio.gather(
        storage.get_json(path="projects/{}/requirements.json".format(project_id), owner=owner, headers=headers),
        storage.get_json(path="projects/{}/workflow.json".format(project_id), owner=owner, headers=headers)
        )
    print("Flux-Backend@Post metadata: got requirements and workflow")
    libraries = {**req['libraries'], **metadata_body.libraries}

    def get_package_id(factory_id: Union[str, Mapping[str, str]]):
        return "@youwol/" + factory_id.split("@")[1] if isinstance(factory_id, str) else factory_id['pack']

    used_packages = {get_package_id(m["factoryId"]) for m in workflow["modules"] + workflow["plugins"]}
    print("Flux-Backend@Post metadata: used_packages", used_packages)

    body = {
        "libraries": {name: version for name, version in libraries.items() if name in used_packages},
        "using":  {name: version for name, version in libraries.items() if 'flux-pack' not in used_packages}
        }
    loading_graph = await configuration.cdn_client.query_loading_graph(body=body, headers=headers)
    print("Flux-Backend@Post metadata: got loading graph", loading_graph)

    used_libraries = {lib["name"]: lib["version"] for lib in loading_graph["lock"]}
    requirements = Requirements(fluxComponents=[], fluxPacks=used_packages,
                                libraries=used_libraries, loadingGraph=loading_graph)

    coroutines = update_metadata(project_id=project_id, name=metadata_body.name,
                                 description=metadata_body.description, requirements=requirements,
                                 owner=owner, storage=storage, docdb=doc_db, headers=headers)
    await asyncio.gather(*coroutines)
    return {}


@router.get("/projects/{project_id}/metadata",
            response_model=ProjectSnippet,
            summary="retrieve the metadata of a project")
async def get_metadata(
        request: Request,
        project_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    owner = configuration.default_owner
    meta = await doc_db.get_document(partition_keys={"project_id": project_id},
                                     clustering_keys={},
                                     owner=owner,
                                     headers=headers)

    return ProjectSnippet(name=meta["name"], id=meta["project_id"], description=meta["description"],
                          fluxPacks=meta["packages"])


@router.post("/projects/{project_id}", summary="post a project")
async def post_project(
        request: Request,
        project_id: str,
        project: Project,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    storage, docdb = configuration.storage, configuration.doc_db
    owner = configuration.default_owner

    coroutines = update_project(project_id=project_id, owner=owner,
                                project=project, storage=storage, docdb=docdb, headers=headers)
    await asyncio.gather(*coroutines)
    return {}


@router.post("/components/{component_id}", summary="post a component")
async def post_component(
        request: Request,
        component_id: str,
        component: Component,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    storage, docdb = configuration.storage, configuration.doc_db_component
    owner = configuration.default_owner

    await update_component(component_id=component_id, owner=owner,
                           component=component, storage=configuration.storage, doc_db_component=docdb,
                           headers=headers)
    return {}


@router.get("/components/{component_id}", summary="post a component")
async def get_component(
        request: Request,
        component_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    owner = configuration.default_owner

    component = await retrieve_component(component_id=component_id, owner=owner, storage=configuration.storage,
                                         doc_db_component=configuration.doc_db_component, headers=headers)
    return component


@router.delete("/components/{component_id}", summary="delete a component")
async def delete_component(
        request: Request,
        component_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    docdb = configuration.doc_db_component

    owner = configuration.default_owner

    base_path = "components/{}".format(component_id)
    storage = configuration.storage
    await asyncio.gather(docdb.delete_document(doc={"component_id": component_id}, owner=owner, headers=headers),
                         storage.delete_group(prefix=base_path, owner=owner, headers=headers))

    return {"status": "deleted", "componentId": component_id}


@router.get("/flux-packs", summary="list of available package")
async def list_packages(
        request: Request,
        namespace=None,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    packages = await configuration.cdn_client.query_packs(namespace=namespace, headers=headers)

    return packages


def group_scope_to_id(scope: str) -> str:
    if scope == 'private':
        return 'private'
    b = str.encode(scope)
    return base64.urlsafe_b64encode(b).decode()


@router.post("/records",
             response_model=RecordsResponse,
             summary="retrieve records definition")
async def records(
        body: GetRecordsBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    doc_db = configuration.doc_db
    storage = configuration.storage

    def get_paths(project_id):
        base = Path('projects')/project_id
        return [base / name for name in ['builderRendering.json', 'description.json', 'requirements.json',
                                         'runnerRendering.json', 'workflow.json']]

    paths = [get_paths(project_id) for project_id in body.ids]
    paths = list(flatten(paths))
    group_id = to_group_id(configuration.default_owner)
    table = RecordsTable(
        id=doc_db.table_name,
        primaryKey=doc_db.table_body.partition_key[0],
        values=body.ids
        )
    keyspace = RecordsKeyspace(
        id=doc_db.keyspace_name,
        groupId=group_id,
        tables=[table]
        )

    bucket = RecordsBucket(
        id=storage.bucket_name,
        groupId=group_id,
        paths=[str(p) for p in paths]
        )
    response = RecordsResponse(
        docdb=RecordsDocDb(keyspaces=[keyspace]),
        storage=RecordsStorage(buckets=[bucket])
        )

    return response
