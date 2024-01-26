# standard library
import asyncio
import itertools
import json
import os
import tempfile
import zipfile

from collections.abc import Coroutine, Mapping
from pathlib import Path

# typing
from typing import Any, Union

# third parties
from fastapi import HTTPException, UploadFile

# Youwol backends
from youwol.backends.flux.backward_compatibility import (
    convert_project_to_current_version,
)
from youwol.backends.flux.configurations import Constants

# Youwol utilities
from youwol.utils import JSON, DocDb, Storage, base64, write_json
from youwol.utils.http_clients.cdn_backend import patch_loading_graph
from youwol.utils.http_clients.flux_backend import (
    BuilderRendering,
    Component,
    DeprecatedData,
    Project,
    Requirements,
    RunnerRendering,
    Workflow,
)

flatten = itertools.chain.from_iterable
Filename = str
Group = str
ProjectId = str


def read_json(folder: Path, name: str) -> JSON:
    return json.loads((folder / name).read_text())


def create_project_from_json(folder: Path) -> Project:
    description = read_json(folder, "description.json")
    if not isinstance(description, dict):
        raise ValueError("description.json is not a JSON dictionary")
    workflow = read_json(folder, "workflow.json")
    if not isinstance(workflow, dict):
        raise ValueError("workflow.json is not a JSON dictionary")
    builder_rendering = read_json(folder, "builderRendering.json")
    if not isinstance(builder_rendering, dict):
        raise ValueError("builder_rendering.json is not a JSON dictionary")
    runner_rendering = read_json(folder, "runnerRendering.json")
    if not isinstance(runner_rendering, dict):
        raise ValueError("runner_rendering.json is not a JSON dictionary")
    requirements = read_json(folder, "requirements.json")
    if not isinstance(requirements, dict):
        raise ValueError("requirements.json is not a JSON dictionary")
    return Project(
        name=description["name"],
        schemaVersion=(
            description["schemaVersion"] if "schemaVersion" in description else "0"
        ),
        description=description["description"],
        workflow=Workflow(**workflow),
        builderRendering=BuilderRendering(**builder_rendering),
        runnerRendering=RunnerRendering(**runner_rendering),
        requirements=Requirements(**requirements),
    )


def update_project(
    project_id: str,
    owner: str,
    project: Project,
    storage: Storage,
    docdb: DocDb,
    headers: dict[str, str],
) -> list[Coroutine]:
    base_path = f"projects/{project_id}"
    description = {
        "description": project.description,
        "name": project.name,
        "schemaVersion": project.schemaVersion,
    }
    post_files_request = [
        (
            storage.post_json(
                path=Constants.workflow_path(base_path),
                json=project.workflow.dict(),
                owner=owner,
                headers=headers,
            )
            if project.workflow
            else None
        ),
        (
            storage.post_json(
                path=Constants.builder_rendering_path(base_path),
                json=project.builderRendering.dict(),
                owner=owner,
                headers=headers,
            )
            if project.builderRendering
            else None
        ),
        (
            storage.post_json(
                path=Constants.runner_rendering_path(base_path),
                json=project.runnerRendering.dict(),
                owner=owner,
                headers=headers,
            )
            if project.runnerRendering
            else None
        ),
        (
            storage.post_json(
                path=Constants.requirements_path(base_path),
                json=project.requirements.dict(),
                owner=owner,
                headers=headers,
            )
            if project.requirements
            else None
        ),
        storage.post_json(
            path=Constants.description_path(base_path),
            json=description,
            owner=owner,
            headers=headers,
        ),
    ]
    document = create_project_document(
        project_id=project_id,
        name=project.name,
        description=description["description"],
        packages=project.requirements.fluxPacks,
        bucket=storage.bucket_name,
        path=base_path,
    )

    docdb_request = docdb.create_document(doc=document, owner=owner, headers=headers)
    return [*[req for req in post_files_request if req], docdb_request]


def update_metadata(
    project_id: str,
    name: str,
    description: str,
    schema_version: str,
    owner: str,
    requirements: Requirements,
    storage: Storage,
    docdb: DocDb,
    headers: dict[str, str],
) -> list[Coroutine]:
    base_path = f"projects/{project_id}"
    struct_description = {
        "description": description,
        "schemaVersion": schema_version,
        "name": name,
    }
    post_files_request = [
        (
            storage.post_json(
                path=f"{base_path}/requirements.json",
                json=requirements.dict(),
                owner=owner,
                headers=headers,
            )
            if requirements
            else None
        ),
        storage.post_json(
            path=f"{base_path}/description.json",
            json=struct_description,
            owner=owner,
            headers=headers,
        ),
    ]
    document = create_project_document(
        project_id=project_id,
        name=name,
        description=struct_description["description"],
        packages=requirements.fluxPacks,
        bucket=storage.bucket_name,
        path=base_path,
    )

    docdb_request = docdb.create_document(doc=document, owner=owner, headers=headers)
    return [*[req for req in post_files_request if req], docdb_request]


async def retrieve_project(
    project_id: str,
    owner: Union[None, str],
    storage: Storage,
    headers: Mapping[str, str],
) -> Project:
    (
        workflow,
        builder_rendering,
        runner_rendering,
        requirements,
        description,
    ) = await asyncio.gather(
        storage.get_json(
            path=f"projects/{project_id}/workflow.json",
            owner=owner,
            headers=headers,
        ),
        storage.get_json(
            path=f"projects/{project_id}/builderRendering.json",
            owner=owner,
            headers=headers,
        ),
        storage.get_json(
            path=f"projects/{project_id}/runnerRendering.json",
            owner=owner,
            headers=headers,
        ),
        storage.get_json(
            path=f"projects/{project_id}/requirements.json",
            owner=owner,
            headers=headers,
        ),
        storage.get_json(
            path=f"projects/{project_id}/description.json",
            owner=owner,
            headers=headers,
        ),
    )

    deprecated_data = DeprecatedData(rootLayerTree={})
    if "rootLayerTree" in workflow:
        deprecated_data = DeprecatedData(rootLayerTree=workflow["rootLayerTree"])
    if requirements["loadingGraph"]["graphType"] != "sequential-v2":
        patch_loading_graph(requirements["loadingGraph"])

    project = Project(
        name=description["name"],
        schemaVersion=(
            description["schemaVersion"] if "schemaVersion" in description else "0"
        ),
        description=description["description"],
        requirements=requirements,
        workflow=Workflow(**workflow),
        builderRendering=BuilderRendering(**builder_rendering),
        runnerRendering=RunnerRendering(**runner_rendering),
    )

    if project.schemaVersion != Constants.current_schema_version:
        project = convert_project_to_current_version(project, deprecated_data)

    return project


async def update_component(
    component_id: str,
    owner: str,
    component: Component,
    storage: Storage,
    doc_db_component: DocDb,
    headers: dict[str, str],
) -> Any:
    base_path = f"components/{component_id}"
    description = {
        "description": component.description,
        "name": component.name,
        "scope": component.scope,
    }
    futures = [
        storage.post_json(
            path=f"{base_path}/workflow.json",
            json=component.workflow.dict(),
            owner=owner,
            headers=headers,
        ),
        storage.post_json(
            path=f"{base_path}/builderRendering.json",
            json=component.builderRendering.dict(),
            owner=owner,
            headers=headers,
        ),
        storage.post_json(
            path=f"{base_path}/requirements.json",
            json={"fluxPacks": component.fluxPacks},
            owner=owner,
            headers=headers,
        ),
        storage.post_json(
            path=f"{base_path}/description.json",
            json=description,
            owner=owner,
            headers=headers,
        ),
    ]
    if component.runnerRendering:
        futures.append(
            storage.post_json(
                path=f"{base_path}/runnerRendering.json",
                json=component.runnerRendering.dict(),
                owner=owner,
                headers=headers,
            )
        )

    await asyncio.gather(*futures)

    doc_db = doc_db_component
    doc = create_component_document(
        component_id=component_id,
        name=component.name,
        description=component.description,
        packages=component.fluxPacks,
        bucket=storage.bucket_name,
        path=base_path,
        has_view=component.runnerRendering is not None,
    )

    await doc_db.update_document(doc=doc, owner=owner, headers=headers)

    return {}


async def retrieve_component(
    component_id: str,
    owner: Union[None, str],
    storage: Storage,
    doc_db_component: DocDb,
    headers: Mapping[str, str],
) -> Component:
    doc_db_response = await doc_db_component.query(
        query_body=f"component_id={component_id}#1", owner=owner, headers=headers
    )

    if not doc_db_response["documents"]:
        raise HTTPException(status_code=404, detail="component not found")

    base_path = f"components/{component_id}"
    futures = [
        storage.get_json(
            path=Constants.workflow_path(base_path), owner=owner, headers=headers
        ),
        storage.get_json(
            path=Constants.builder_rendering_path(base_path),
            owner=owner,
            headers=headers,
        ),
        storage.get_json(
            path=Constants.requirements_path(base_path), owner=owner, headers=headers
        ),
        storage.get_json(
            path=Constants.description_path(base_path), owner=owner, headers=headers
        ),
    ]
    has_view = doc_db_response["documents"][0]["has_view"]
    if has_view:
        futures.append(
            storage.get_json(
                path=Constants.runner_rendering_path(base_path),
                owner=owner,
                headers=headers,
            )
        )
    components = await asyncio.gather(*futures)

    workflow, builder_rendering, requirements, description = components[0:4]

    component = Component(
        name=description["name"],
        description=description["description"],
        scope=description["scope"],
        fluxPacks=requirements["fluxPacks"],
        workflow=Workflow(**workflow),
        builderRendering=BuilderRendering(**builder_rendering),
        runnerRendering=RunnerRendering(**components[-1]) if has_view else None,
    )

    return component


def extract_zip_file(
    file: UploadFile, zip_path: Union[Path, str], dir_path: Union[Path, str]
):
    dir_path = str(dir_path)
    with open(zip_path, "ab") as f:
        for chunk in iter(lambda: file.file.read(10000), b""):
            f.write(chunk)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(dir_path)

    os.remove(zip_path)


def zip_project(project) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_folder:
        base_path = Path(tmp_folder)
        write_json(data=project["requirements"], path=base_path / "requirements.json")
        description = {
            "description": project["description"],
            "schemaVersion": project["schemaVersion"],
            "name": project["name"],
        }
        write_json(data=description, path=base_path / "description.json")
        write_json(data=project["workflow"], path=base_path / "workflow.json")
        write_json(
            data=project["runnerRendering"], path=base_path / "runnerRendering.json"
        )
        write_json(
            data=project["builderRendering"], path=base_path / "builderRendering.json"
        )

        with zipfile.ZipFile(
            base_path / "story.zip", "w", zipfile.ZIP_DEFLATED
        ) as zipper:
            for filename in [
                "requirements.json",
                "description.json",
                "workflow.json",
                "runnerRendering.json",
                "builderRendering.json",
            ]:
                zipper.write(base_path / filename, arcname=filename)

        return (Path(tmp_folder) / "story.zip").read_bytes()


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


def create_component_document(
    component_id, name, description, packages, bucket, path, has_view
):
    return {
        "component_id": component_id,
        "bucket": bucket,
        "description": description,
        "name": name,
        "packages": packages,
        "path": path,
        "has_view": has_view,
    }


async def get_json_files(base_path: str, files: list[str], storage, headers):
    futures = [
        storage.get_json(path=base_path + "/" + f, headers=headers) for f in files
    ]
    return await asyncio.gather(*futures)


async def post_json_files(
    base_path: str, files: list[tuple[str, Any]], storage, headers
):
    futures = [
        storage.post_json(path=base_path + "/" + name, json=data, headers=headers)
        for name, data in files
    ]
    return await asyncio.gather(*futures)


def to_group_id(group_path: str) -> str:
    if group_path == "private":
        return "private"
    b = str.encode(group_path)
    return base64.urlsafe_b64encode(b).decode()


def to_group_scope(group_id: str) -> str:
    if group_id == "private":
        return "private"
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()
