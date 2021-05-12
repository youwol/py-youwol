import asyncio
import itertools
import json
import os
import zipfile
from pathlib import Path
from typing import Union, List, Tuple, Coroutine, NamedTuple, Mapping
from uuid import uuid4

from fastapi import UploadFile, HTTPException

from .configurations import Configuration
from youwol_utils import JSON, DocDb, Storage, base64
from .models import Workflow, BuilderRendering, RunnerRendering, Project, Component, Requirements

flatten = itertools.chain.from_iterable
Filename = str
Group = str
ProjectId = str


class Constants(NamedTuple):
    user_group = None
    public_group: str = "/youwol-users"
    wf_root_layer = {"layerId": "rootLayer", "title": "rootLayer", "children": [], "moduleIds": []}


async def init_resources(config: Configuration):
    print("Init database resources")
    headers = await config.admin_headers if config.admin_headers else {}

    await asyncio.gather(
        config.doc_db_component.ensure_table(headers=headers),
        config.doc_db.ensure_table(headers=headers),
        config.storage.ensure_bucket(headers=headers)
        )


def read_json(folder: Path, name: str) -> JSON:
    return json.loads((folder / name).read_text())


def create_project_from_json(folder: Path) -> (ProjectId, Project):

    description = read_json(folder, "description.json")
    workflow = read_json(folder, "workflow.json")
    builder_rendering = read_json(folder, "builderRendering.json")
    runner_rendering = read_json(folder, "runnerRendering.json")
    requirements = read_json(folder, "requirements.json")
    project = Project(name=description["name"],
                      description=description["description"],
                      workflow=Workflow(**workflow),
                      builderRendering=BuilderRendering(**builder_rendering),
                      runnerRendering=RunnerRendering(**runner_rendering),
                      requirements=Requirements(**requirements))
    return str(folder), project


def update_project(project_id: str, owner: Union[str, None], project: Project, storage: Storage,
                   docdb: DocDb, headers: Mapping[str, str]) -> List[Coroutine]:

    base_path = f"projects/{project_id}"
    description = {"description": project.description, "name": project.name}
    post_files_request = [
        storage.post_json(path="{}/workflow.json".format(base_path), json=project.workflow.dict(), owner=owner,
                          headers=headers) if project.workflow else None,
        storage.post_json(path="{}/builderRendering.json".format(base_path), json=project.builderRendering.dict(),
                          owner=owner, headers=headers) if project.builderRendering else None,
        storage.post_json(path="{}/runnerRendering.json".format(base_path), json=project.runnerRendering.dict(),
                          owner=owner, headers=headers) if project.runnerRendering else None,
        storage.post_json(path="{}/requirements.json".format(base_path), json=project.requirements.dict(), owner=owner,
                          headers=headers) if project.requirements else None,
        storage.post_json(path="{}/description.json".format(base_path), json=description, owner=owner,
                          headers=headers)
        ]
    post_files_request = [req for req in post_files_request if req]
    document = create_project_document(project_id=project_id, name=project.name, description=description["description"],
                                       packages=project.requirements.fluxPacks, bucket=storage.bucket_name,
                                       path=base_path)

    docdb_request = docdb.create_document(doc=document, owner=owner, headers=headers)
    return [*post_files_request, docdb_request]


def update_metadata(project_id: str, name: str, description: str, owner: Union[str, None],
                    requirements: Requirements, storage: Storage, docdb: DocDb, headers: Mapping[str, str]) \
        -> List[Coroutine]:

    base_path = f"projects/{project_id}"
    description = {"description": description, "name": name}
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


async def retrieve_project(project_id: str, owner: Union[None, str], storage: Storage,  docdb: DocDb,
                           headers: Mapping[str, str]) \
        -> (Project, Group):

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

    project = Project(name=description["name"], description=description["description"], requirements=requirements,
                      workflow=Workflow(**workflow), builderRendering=BuilderRendering(**builder_rendering),
                      runnerRendering=RunnerRendering(**runner_rendering))

    return project


async def update_component(component_id: str, owner: Union[str, None], component: Component, storage: Storage,
                           doc_db_component: DocDb, headers: Mapping[str, str])\
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

    doc_db_response = await doc_db_component.query(
        where_clauses=[{"column": "component_id", "relation": "eq", "term": component_id}],
        select_clauses=[], ordering_clauses=[], owner=owner, max_results=1, allow_filtering=True, headers=headers)

    if not doc_db_response["documents"]:
        raise HTTPException(status_code=404, detail="component not found")

    base_path = "components/{}".format(component_id)
    futures = [
        storage.get_json(path=f"{base_path}/workflow.json", owner=owner, headers=headers),
        storage.get_json(path=f"{base_path}/builderRendering.json", owner=owner, headers=headers),
        storage.get_json(path=f"{base_path}/requirements.json", owner=owner, headers=headers),
        storage.get_json(path=f"{base_path}/description.json", owner=owner, headers=headers)
        ]
    has_view = doc_db_response["documents"][0]["has_view"]
    if has_view:
        futures.append(storage.get_json(path=f"{base_path}/runnerRendering.json", owner=owner, headers=headers))
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


"""
def get_content_encoding(file_id):
    if ".js" in file_id or ".css" in file_id:
        return "br"
    return "identity"
"""


async def get_json_files(base_path: str, files: List[str], storage, headers):

    futures = [storage.get_json(path=base_path + "/" + f, headers=headers)for f in files]
    return await asyncio.gather(*futures)


async def post_json_files(base_path: str, files: List[Tuple[str, any]], storage, headers):

    futures = [storage.post_json(path=base_path + "/" + name, json=data, headers=headers)for name, data in files]
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
