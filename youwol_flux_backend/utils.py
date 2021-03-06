import asyncio
import itertools
import json
import os
import zipfile
from pathlib import Path
from typing import Union, List, Tuple, Coroutine, Mapping
from uuid import uuid4

from fastapi import UploadFile, HTTPException

from youwol_utils import JSON, DocDb, Storage, base64, log_info
from youwol_flux_backend.backward_compatibility import convert_project_to_current_version
from youwol_flux_backend.configurations import Configuration, Constants
from youwol_utils.http_clients.flux_backend import (
    Workflow, BuilderRendering, RunnerRendering, Project, Component, Requirements, DeprecatedData
)

flatten = itertools.chain.from_iterable
Filename = str
Group = str
ProjectId = str


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = config.admin_headers if config.admin_headers else {}

    log_info("Successfully retrieved authorization for resources creation")
    await asyncio.gather(
        config.doc_db_component.ensure_table(headers=headers),
        config.doc_db.ensure_table(headers=headers),
        config.storage.ensure_bucket(headers=headers)
    )
    log_info("resources initialization done")


def read_json(folder: Path, name: str) -> JSON:
    return json.loads((folder / name).read_text())


def create_project_from_json(folder: Path) -> Project:
    description = read_json(folder, "description.json")
    workflow = read_json(folder, "workflow.json")
    builder_rendering = read_json(folder, "builderRendering.json")
    runner_rendering = read_json(folder, "runnerRendering.json")
    requirements = read_json(folder, "requirements.json")
    return Project(
        name=description["name"],
        schemaVersion=description["schemaVersion"] if "schemaVersion" in description else "0",
        description=description["description"],
        workflow=Workflow(**workflow),
        builderRendering=BuilderRendering(**builder_rendering),
        runnerRendering=RunnerRendering(**runner_rendering),
        requirements=Requirements(**requirements)
    )


def update_project(project_id: str, owner: Union[str, None], project: Project, storage: Storage,
                   docdb: DocDb, headers: Mapping[str, str]) -> List[Coroutine]:
    base_path = f"projects/{project_id}"
    description = {"description": project.description, "name": project.name, "schemaVersion": project.schemaVersion}
    post_files_request = [
        storage.post_json(path=Constants.workflow_path(base_path), json=project.workflow.dict(), owner=owner,
                          headers=headers) if project.workflow else None,
        storage.post_json(path=Constants.builder_rendering_path(base_path), json=project.builderRendering.dict(),
                          owner=owner, headers=headers) if project.builderRendering else None,
        storage.post_json(path=Constants.runner_rendering_path(base_path), json=project.runnerRendering.dict(),
                          owner=owner, headers=headers) if project.runnerRendering else None,
        storage.post_json(path=Constants.requirements_path(base_path), json=project.requirements.dict(), owner=owner,
                          headers=headers) if project.requirements else None,
        storage.post_json(path=Constants.description_path(base_path), json=description, owner=owner,
                          headers=headers)
    ]
    post_files_request = [req for req in post_files_request if req]
    document = create_project_document(project_id=project_id, name=project.name, description=description["description"],
                                       packages=project.requirements.fluxPacks, bucket=storage.bucket_name,
                                       path=base_path)

    docdb_request = docdb.create_document(doc=document, owner=owner, headers=headers)
    return [*post_files_request, docdb_request]


def update_metadata(project_id: str, name: str, description: str, schema_version: str, owner: Union[str, None],
                    requirements: Requirements, storage: Storage, docdb: DocDb, headers: Mapping[str, str]) \
        -> List[Coroutine]:
    base_path = f"projects/{project_id}"
    description = {"description": description, "schemaVersion": schema_version, "name": name}
    post_files_request = [
        storage.post_json(path="{}/requirements.json".format(base_path), json=requirements.dict(), owner=owner,
                          headers=headers) if requirements else None,
        storage.post_json(path="{}/description.json".format(base_path), json=description, owner=owner,
                          headers=headers)
    ]
    post_files_request = [req for req in post_files_request if req]
    document = create_project_document(project_id=project_id, name=name, description=description["description"],
                                       packages=requirements.fluxPacks, bucket=storage.bucket_name, path=base_path)

    docdb_request = docdb.create_document(doc=document, owner=owner, headers=headers)
    return [*post_files_request, docdb_request]


async def retrieve_project(
        project_id: str,
        owner: Union[None, str],
        storage: Storage,
        headers: Mapping[str, str]
) \
        -> (Project, Group, dict):
    workflow, builder_rendering, runner_rendering, requirements, description = await asyncio.gather(
        storage.get_json(path="projects/{}/workflow.json".format(project_id),
                         owner=owner, headers=headers),
        storage.get_json(path="projects/{}/builderRendering.json".format(project_id),
                         owner=owner, headers=headers),
        storage.get_json(path="projects/{}/runnerRendering.json".format(project_id),
                         owner=owner, headers=headers),
        storage.get_json(path="projects/{}/requirements.json".format(project_id),
                         owner=owner, headers=headers),
        storage.get_json(path="projects/{}/description.json".format(project_id),
                         owner=owner, headers=headers)
    )

    deprecated_data = {}
    if 'rootLayerTree' in workflow:
        deprecated_data = DeprecatedData(rootLayerTree=workflow['rootLayerTree'])

    project = Project(name=description["name"],
                      schemaVersion=description["schemaVersion"] if "schemaVersion" in description else "0",
                      description=description["description"],
                      requirements=requirements,
                      workflow=Workflow(**workflow),
                      builderRendering=BuilderRendering(**builder_rendering),
                      runnerRendering=RunnerRendering(**runner_rendering)
                      )

    if project.schemaVersion != Constants.current_schema_version:
        project = convert_project_to_current_version(project, deprecated_data)

    return project


async def update_component(component_id: str, owner: Union[str, None], component: Component, storage: Storage,
                           doc_db_component: DocDb, headers: Mapping[str, str]) \
        -> any:
    base_path = "components/{}".format(component_id)
    description = {"description": component.description, "name": component.name, "scope": component.scope}
    futures = [
        storage.post_json(path="{}/workflow.json".format(base_path),
                          json=component.workflow.dict(),
                          owner=owner,
                          headers=headers),
        storage.post_json(path="{}/builderRendering.json".format(base_path),
                          json=component.builderRendering.dict(),
                          owner=owner,
                          headers=headers),
        storage.post_json(path="{}/requirements.json".format(base_path),
                          json={"fluxPacks": component.fluxPacks},
                          owner=owner,
                          headers=headers),
        storage.post_json(path="{}/description.json".format(base_path),
                          json=description,
                          owner=owner,
                          headers=headers)
    ]
    if component.runnerRendering:
        futures.append(
            storage.post_json(path="{}/runnerRendering.json".format(base_path),
                              json=component.runnerRendering.dict(),
                              owner=owner,
                              headers=headers))

    await asyncio.gather(*futures)

    doc_db = doc_db_component
    doc = create_component_document(
        component_id=component_id, name=component.name, description=component.description,
        packages=component.fluxPacks, bucket=storage.bucket_name, path=base_path,
        has_view=component.runnerRendering is not None)

    await doc_db.update_document(doc=doc, owner=owner, headers=headers)

    return {}


async def retrieve_component(component_id: str, owner: Union[None, str], storage: Storage,
                             doc_db_component: DocDb, headers: Mapping[str, str]) -> Component:
    doc_db_response = await doc_db_component.query(query_body=f"component_id={component_id}#1", owner=owner,
                                                   headers=headers)

    if not doc_db_response["documents"]:
        raise HTTPException(status_code=404, detail="component not found")

    base_path = "components/{}".format(component_id)
    futures = [
        storage.get_json(path=Constants.workflow_path(base_path), owner=owner, headers=headers),
        storage.get_json(path=Constants.builder_rendering_path(base_path), owner=owner, headers=headers),
        storage.get_json(path=Constants.requirements_path(base_path), owner=owner, headers=headers),
        storage.get_json(path=Constants.description_path(base_path), owner=owner, headers=headers)
    ]
    has_view = doc_db_response["documents"][0]["has_view"]
    if has_view:
        futures.append(storage.get_json(path=Constants.runner_rendering_path(base_path), owner=owner, headers=headers))
    components = await asyncio.gather(*futures)

    workflow, builder_rendering, requirements, description = components[0:4]

    component = Component(name=description["name"], description=description["description"], scope=description["scope"],
                          fluxPacks=requirements["fluxPacks"], workflow=Workflow(**workflow),
                          builderRendering=BuilderRendering(**builder_rendering),
                          runnerRendering=RunnerRendering(**components[-1]) if has_view else None)

    return component


def create_tmp_folder(zip_filename):
    dir_path = Path("./tmp_zips") / str(uuid4())
    zip_path = (dir_path / zip_filename).with_suffix('.zip')
    zip_dir_name = zip_filename.split('.')[0]
    os.makedirs(dir_path)
    return dir_path, zip_path, zip_dir_name


def extract_zip_file(file: UploadFile, zip_path: Union[Path, str], dir_path: Union[Path, str]):
    dir_path = str(dir_path)
    with open(zip_path, 'ab') as f:
        for chunk in iter(lambda: file.file.read(10000), b''):
            f.write(chunk)

    compressed_size = zip_path.stat().st_size
    md5_stamp = os.popen('md5sum ' + str(zip_path)).read().split(" ")[0]

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dir_path)

    os.remove(zip_path)
    return compressed_size, md5_stamp


def to_directory_name(name):
    return name


def create_project_document(project_id, name, description, packages, bucket, path):
    return {
        "project_id": project_id,
        "bucket": bucket,
        "description": description,
        "name": name,
        "packages": packages,
        "path": path,
    }


def create_component_document(component_id, name, description, packages, bucket, path, has_view):
    return {
        "component_id": component_id,
        "bucket": bucket,
        "description": description,
        "name": name,
        "packages": packages,
        "path": path,
        "has_view": has_view
    }


async def get_json_files(base_path: str, files: List[str], storage, headers):
    futures = [storage.get_json(path=base_path + "/" + f, headers=headers) for f in files]
    return await asyncio.gather(*futures)


async def post_json_files(base_path: str, files: List[Tuple[str, any]], storage, headers):
    futures = [storage.post_json(path=base_path + "/" + name, json=data, headers=headers) for name, data in files]
    return await asyncio.gather(*futures)


def to_group_id(group_path: str) -> str:
    if group_path == 'private':
        return 'private'
    b = str.encode(group_path)
    return base64.urlsafe_b64encode(b).decode()


def to_group_scope(group_id: str) -> str:
    if group_id == 'private':
        return 'private'
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()
