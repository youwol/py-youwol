# standard library
import base64
import io
import itertools
import json
import os
import tempfile
import uuid
import zipfile

from pathlib import Path

# typing
from typing import Mapping, Union

# third parties
from fastapi import APIRouter, Depends, File, HTTPException
from fastapi import Query as QueryParam
from fastapi import UploadFile
from starlette.responses import StreamingResponse

# Youwol utilities
from youwol.utils import (
    GetRecordsBody,
    Query,
    QueryBody,
    RecordsBucket,
    RecordsDocDb,
    RecordsKeyspace,
    RecordsResponse,
    RecordsStorage,
    RecordsTable,
    Request,
    asyncio,
    check_permission_or_raise,
    get_all_individual_groups,
    to_group_id,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import PublishResponse, patch_loading_graph
from youwol.utils.http_clients.flux_backend import (
    BuilderRendering,
    Component,
    EditMetadata,
    LoadingGraph,
    NewProject,
    NewProjectResponse,
    Project,
    Projects,
    ProjectSnippet,
    PublishApplicationBody,
    Requirements,
    RunnerRendering,
)
from youwol.utils.utils_paths import write_json

# relative
from .configurations import Configuration, Constants, get_configuration
from .utils import (
    create_project_from_json,
    extract_zip_file,
    retrieve_component,
    retrieve_project,
    update_component,
    update_metadata,
    update_project,
)
from .workflow_new_project import workflow_new_project

router = APIRouter(tags=["flux-backend"])
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "flux-backend serving"}


@router.get(
    "/projects", response_model=Projects, summary="retrieve the list of projects"
)
async def list_projects(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        doc_db = configuration.doc_db
        user = user_info(request)
        groups = get_all_individual_groups(user["memberof"])
        requests = [
            doc_db.query(
                query_body=QueryBody(query=Query()), owner=group, headers=ctx.headers()
            )
            for group in groups
        ]
        projects = await asyncio.gather(*requests)
        flatten_groups = list(
            flatten(
                [
                    len(project["documents"]) * [groups[i]]
                    for i, project in enumerate(projects)
                ]
            )
        )
        flatten_projects = list(flatten([project["documents"] for project in projects]))

        snippets = [
            ProjectSnippet(
                name=r["name"],
                id=r["project_id"],
                description=r["description"],
                fluxPacks=r["packages"],
            )
            for r, group in zip(flatten_projects, flatten_groups)
        ]

        return Projects(projects=snippets)


@router.get(
    "/projects/{project_id}", response_model=Project, summary="retrieve a project"
)
async def get_project(
    request: Request,
    project_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        owner = Constants.default_owner

        project = await retrieve_project(
            project_id=project_id,
            owner=owner,
            storage=configuration.storage,
            headers=ctx.headers(),
        )

        return project


@router.post(
    "/projects/create",
    summary="create a new project",
    response_model=NewProjectResponse,
)
async def new_project(
    request: Request,
    project_body: NewProject,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        project_id = project_body.projectId or str(uuid.uuid4())
        workflow = workflow_new_project
        builder_rendering = BuilderRendering(
            modulesView=[], connectionsView=[], descriptionsBoxes=[]
        )
        runner_rendering = RunnerRendering(layout="", style="")
        requirements = Requirements(
            fluxPacks=[],
            fluxComponents=[],
            libraries={},
            loadingGraph=LoadingGraph(
                graphType="sequential-v2", lock=[], definition=[[]]
            ),
        )

        project = Project(
            name=project_body.name,
            schemaVersion=Constants.current_schema_version,
            description=project_body.description,
            workflow=workflow,
            builderRendering=builder_rendering,
            runnerRendering=runner_rendering,
            requirements=requirements,
        )

        coroutines = update_project(
            project_id=project_id,
            owner=Constants.default_owner,
            project=project,
            storage=configuration.storage,
            docdb=configuration.doc_db,
            headers=ctx.headers(),
        )
        await asyncio.gather(*coroutines)
        return NewProjectResponse(
            projectId=project_id, libraries=requirements.libraries
        )


@router.post(
    "/projects/{project_id}/duplicate",
    summary="duplicate a project",
    response_model=NewProjectResponse,
)
async def duplicate(
    request: Request,
    project_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        owner = Constants.default_owner
        project = await retrieve_project(
            project_id=project_id,
            owner=owner,
            storage=configuration.storage,
            headers=ctx.headers(),
        )

        project_id = str(uuid.uuid4())

        coroutines = update_project(
            project_id=project_id,
            project=project,
            owner=owner,
            storage=configuration.storage,
            docdb=configuration.doc_db,
            headers=ctx.headers(),
        )
        await asyncio.gather(*coroutines)

        return NewProjectResponse(
            projectId=project_id, libraries=project.requirements.libraries
        )


@router.post("/projects/upload", summary="upload projects")
async def upload(
    request: Request,
    project_id: str = QueryParam(None, alias="project-id"),
    file: UploadFile = File(...),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            zip_path = dir_path / "upload.zip"
            extract_zip_file(file, zip_path, dir_path)
            files = os.listdir(dir_path)
            await ctx.info("Zip extracted", data={"files": files})
            project = create_project_from_json(dir_path)
            project_id = project_id or str(uuid.uuid4())
            await asyncio.gather(
                *update_project(
                    project_id=project_id,
                    owner=Constants.default_owner,
                    project=project,
                    storage=configuration.storage,
                    docdb=configuration.doc_db,
                    headers=ctx.headers(),
                )
            )
            return NewProjectResponse(
                projectId=project_id, libraries=project.requirements.libraries
            )


@router.get(
    "/projects/{project_id}/download-zip", summary="download a project as zip file"
)
async def download_zip(
    request: Request,
    project_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        action="download zip", request=request
    ) as ctx:  # type: Context
        owner = Constants.default_owner
        project = await retrieve_project(
            project_id=project_id,
            owner=owner,
            storage=configuration.storage,
            headers=ctx.headers(),
        )
        project = project.dict()
        await ctx.info(text="Project retrieved")

        with tempfile.TemporaryDirectory() as tmp_folder:
            base_path = Path(tmp_folder)
            with zipfile.ZipFile(
                base_path / "flux-project.zip", "w", zipfile.ZIP_DEFLATED
            ) as zipper:
                for file in [
                    "workflow",
                    "runnerRendering",
                    "requirements",
                    "description",
                    "builderRendering",
                ]:
                    if file == "description":
                        description = {
                            "description": project["description"],
                            "name": project["name"],
                            "schemaVersion": project["schemaVersion"],
                        }
                        write_json(data=description, path=base_path / f"{file}.json")
                    else:
                        write_json(data=project[file], path=base_path / f"{file}.json")
                    zipper.write(base_path / f"{file}.json", arcname=f"{file}.json")

            content_bytes = (Path(tmp_folder) / "flux-project.zip").read_bytes()
            return StreamingResponse(
                io.BytesIO(content_bytes), media_type="application/zip"
            )


@router.delete("/projects/{project_id}", summary="delete a project")
async def delete_project(
    request: Request,
    project_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        doc_db = configuration.doc_db
        user = user_info(request)
        group = Constants.default_owner

        if group == -1:
            raise HTTPException(
                status_code=404, detail="delete_project: project not found"
            )

        check_permission_or_raise(group, user["memberof"])

        base_path = f"projects/{project_id}"
        storage = configuration.storage
        await doc_db.delete_document(
            doc={"project_id": project_id}, owner=group, headers=ctx.headers()
        )
        await storage.delete_group(prefix=base_path, owner=group, headers=ctx.headers())

        return {"status": "deleted", "projectId": project_id}


@router.post("/projects/{project_id}/metadata", summary="edit metadata of a project")
async def post_metadata(
    request: Request,
    project_id: str,
    metadata_body: EditMetadata,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        action="update requirements", request=request
    ) as ctx:  # type: Context
        doc_db, storage, assets_gtw = (
            configuration.doc_db,
            configuration.storage,
            configuration.assets_gtw_client,
        )
        owner = Constants.default_owner

        actual_requirements, workflow, description = await asyncio.gather(
            storage.get_json(
                path=f"projects/{project_id}/requirements.json",
                owner=owner,
                headers=ctx.headers(),
            ),
            storage.get_json(
                path=f"projects/{project_id}/workflow.json",
                owner=owner,
                headers=ctx.headers(),
            ),
            storage.get_json(
                path=f"projects/{project_id}/description.json",
                owner=owner,
                headers=ctx.headers(),
            ),
        )
        if actual_requirements["loadingGraph"]["graphType"] != "sequential-v2":
            patch_loading_graph(actual_requirements["loadingGraph"])

        actual_requirements = Requirements(**actual_requirements)
        await ctx.info(
            "Requirements and workflow retrieved",
            data={"requirements": actual_requirements},
        )
        new_requirements = None
        if metadata_body.libraries:
            libraries = {**actual_requirements.libraries, **metadata_body.libraries}

            def get_package_id(factory_id: Union[str, Mapping[str, str]]):
                return (
                    "@youwol/" + factory_id.split("@")[1]
                    if isinstance(factory_id, str)
                    else factory_id["pack"]
                )

            used_packages = {
                get_package_id(m["factoryId"])
                for m in workflow["modules"] + workflow["plugins"]
            }
            await ctx.info("used_packages", data={"usedPackages": used_packages})

            body = {
                "libraries": {
                    name: version
                    for name, version in libraries.items()
                    if name in used_packages
                },
                "using": dict(libraries.items()),
            }
            loading_graph = (
                await assets_gtw.get_cdn_backend_router().query_loading_graph(
                    body=body, headers=ctx.headers()
                )
            )

            flux_packs = [
                p["name"] for p in loading_graph["lock"] if p["type"] == "flux-pack"
            ]
            await ctx.info(
                "loading graph retrieved", data={"loading graph": loading_graph}
            )

            used_libraries = {
                lib["name"]: lib["version"] for lib in loading_graph["lock"]
            }
            new_requirements = Requirements(
                fluxComponents=[],
                fluxPacks=flux_packs,
                libraries=used_libraries,
                loadingGraph=loading_graph,
            )
            await ctx.info(
                "requirements re-computed", data={"requirements": new_requirements}
            )

        schema_version = (
            description["schemaVersion"] if "schemaVersion" in description else "0"
        )
        coroutines = update_metadata(
            project_id=project_id,
            schema_version=schema_version,
            name=metadata_body.name or description["name"],
            description=metadata_body.description or description["description"],
            requirements=new_requirements or actual_requirements,
            owner=owner,
            storage=storage,
            docdb=doc_db,
            headers=ctx.headers(),
        )
        await asyncio.gather(*coroutines)
        return {}


@router.get(
    "/projects/{project_id}/metadata",
    response_model=ProjectSnippet,
    summary="retrieve the metadata of a project",
)
async def get_metadata(
    request: Request,
    project_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        doc_db = configuration.doc_db
        owner = Constants.default_owner
        meta = await doc_db.get_document(
            partition_keys={"project_id": project_id},
            clustering_keys={},
            owner=owner,
            headers=ctx.headers(),
        )

        return ProjectSnippet(
            name=meta["name"],
            id=meta["project_id"],
            description=meta["description"],
            fluxPacks=meta["packages"],
        )


@router.post("/projects/{project_id}", summary="post a project")
async def post_project(
    request: Request,
    project_id: str,
    project: Project,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        storage, docdb = configuration.storage, configuration.doc_db
        owner = Constants.default_owner

        coroutines = update_project(
            project_id=project_id,
            owner=owner,
            project=project,
            storage=storage,
            docdb=docdb,
            headers=ctx.headers(),
        )
        await asyncio.gather(*coroutines)
        return {}


@router.post("/components/{component_id}", summary="post a component")
async def post_component(
    request: Request,
    component_id: str,
    component: Component,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        _, docdb = configuration.storage, configuration.doc_db_component
        owner = Constants.default_owner

        await update_component(
            component_id=component_id,
            owner=owner,
            component=component,
            storage=configuration.storage,
            doc_db_component=docdb,
            headers=ctx.headers(),
        )
        return {}


@router.get("/components/{component_id}", summary="post a component")
async def get_component(
    request: Request,
    component_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        owner = Constants.default_owner
        component = await retrieve_component(
            component_id=component_id,
            owner=owner,
            storage=configuration.storage,
            doc_db_component=configuration.doc_db_component,
            headers=ctx.headers(),
        )
        return component


@router.delete("/components/{component_id}", summary="delete a component")
async def delete_component(
    request: Request,
    component_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        docdb = configuration.doc_db_component

        owner = Constants.default_owner

        base_path = f"components/{component_id}"
        storage = configuration.storage
        await asyncio.gather(
            docdb.delete_document(
                doc={"component_id": component_id}, owner=owner, headers=ctx.headers()
            ),
            storage.delete_group(prefix=base_path, owner=owner, headers=ctx.headers()),
        )

        return {"status": "deleted", "componentId": component_id}


@router.post(
    "/projects/{project_id}/publish-application",
    response_model=PublishResponse,
    summary="retrieve records definition",
)
async def publish_application(
    request: Request,
    project_id: str,
    body: PublishApplicationBody,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Process to update 'bundle_app_template' from flux-runner:
    -  copy all files from 'flux-runner/dist' in it
    -  in index.html:
        -  replace the "<title>...</title>" by "<title>${title}</title>"
        -  replace "<base href='...' />" by "<base href='/applications/${name}/0.0.1/' />"
    -  in on-load_ts...js:
        -  replace "loadProjectById(projectId)" by "loadProjectByUrl('project.json')"
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        base_path = Path(__file__).parent / "bundle_app_template"
        project = await retrieve_project(
            project_id=project_id,
            owner=Constants.default_owner,
            storage=configuration.storage,
            headers=ctx.headers(),
        )
        project.builderRendering = BuilderRendering(modulesView=[], connectionsView=[])

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w") as zip_file:
            for file in base_path.iterdir():
                if file.is_file():
                    content = file.read_text()
                    content = content.replace("${title}", body.displayName).replace(
                        "${name}", body.name
                    )
                    zip_file.writestr(file.name, content)

            zip_file.writestr(
                "/package.json",
                json.dumps(
                    {"name": body.name, "version": body.version, "main": "index.html"}
                ),
            )
            zip_file.writestr("/project.json", json.dumps(project.dict()))
            metadata = {
                "family": "application",
                "displayName": body.displayName,
                "execution": body.execution.dict(),
                "graphics": body.graphics.dict(),
            }
            zip_file.writestr("/.yw_metadata.json", json.dumps(metadata))

        return await configuration.cdn_client.publish(
            zip_content=mem_zip.getvalue(), headers=ctx.headers()
        )


def group_scope_to_id(scope: str) -> str:
    if scope == "private":
        return "private"
    b = str.encode(scope)
    return base64.urlsafe_b64encode(b).decode()


@router.post(
    "/records", response_model=RecordsResponse, summary="retrieve records definition"
)
async def records(
    body: GetRecordsBody, configuration: Configuration = Depends(get_configuration)
):
    doc_db = configuration.doc_db
    storage = configuration.storage

    def get_paths(project_id):
        base = Path("projects") / project_id
        return [
            base / name
            for name in [
                "builderRendering.json",
                "description.json",
                "requirements.json",
                "runnerRendering.json",
                "workflow.json",
            ]
        ]

    paths = [get_paths(project_id) for project_id in body.ids]
    paths = list(flatten(paths))
    group_id = to_group_id(Constants.default_owner)
    table = RecordsTable(
        id=doc_db.table_name,
        primaryKey=doc_db.table_body.partition_key[0],
        values=body.ids,
    )
    keyspace = RecordsKeyspace(
        id=doc_db.keyspace_name, groupId=group_id, tables=[table]
    )

    bucket = RecordsBucket(
        id=storage.bucket_name, groupId=group_id, paths=[str(p) for p in paths]
    )
    response = RecordsResponse(
        docdb=RecordsDocDb(keyspaces=[keyspace]),
        storage=RecordsStorage(buckets=[bucket]),
    )

    return response
