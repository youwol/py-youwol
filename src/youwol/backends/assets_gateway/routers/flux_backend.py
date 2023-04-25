# standard library
import asyncio

# third parties
from fastapi import APIRouter, Depends, Query
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.assets_gateway.configurations import (
    Configuration,
    get_configuration,
)
from youwol.backends.assets_gateway.routers.common import (
    assert_read_permissions_from_raw_id,
    assert_write_permissions_folder_id,
    assert_write_permissions_from_raw_id,
    create_asset,
    delete_asset,
)
from youwol.backends.assets_gateway.utils import AssetMeta

# Youwol utilities
from youwol.utils import encode_id
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_gateway import NewAssetResponse
from youwol.utils.http_clients.flux_backend import (
    EditMetadata,
    NewProject,
    Project,
    ProjectSnippet,
    PublishApplicationBody,
)

router = APIRouter(tags=["assets-gateway.flux-backend"])


@router.post(
    "/projects/create", summary="create a new project", response_model=NewAssetResponse
)
async def new_project(
    request: Request,
    project_body: NewProject,
    folder_id: str = Query(None, alias="folder-id"),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        project = await configuration.flux_client.create_project(
            body=project_body.dict(), headers=ctx.headers()
        )
        return await create_asset(
            request=request,
            kind="flux-project",
            raw_id=project["projectId"],
            raw_response=project,
            folder_id=folder_id,
            metadata=AssetMeta(name=project_body.name),
            context=ctx,
            configuration=configuration,
        )


@router.post("/projects/upload", summary="upload projects")
async def upload(
    request: Request,
    project_id: str = Query(None, alias="project-id"),
    folder_id: str = Query(None, alias="folder-id"),
    name: str = Query(None, alias="name"),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        form = await request.form()
        form = {
            "file": await form.get("file").read(),
            "content_encoding": form.get("content_encoding", "identity"),
        }
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        project = await configuration.flux_client.upload_project(
            data=form,
            project_id=project_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        return await create_asset(
            request=request,
            kind="flux-project",
            raw_id=project["projectId"],
            raw_response=project,
            folder_id=folder_id,
            metadata=AssetMeta(name=name),
            context=ctx,
            configuration=configuration,
        )


@router.get(
    "/projects/{project_id}/download-zip", summary="download a project as zip file"
)
async def download_zip(
    request: Request,
    project_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=project_id, configuration=configuration, context=ctx
        )
        content = await configuration.flux_client.download_zip(
            project_id=project_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        return Response(content=content, headers={"content-type": "application/zip"})


async def delete_project_impl(
    project_id: str, purge: bool, configuration: Configuration, context: Context
):
    async with context.start(action="delete_project_impl") as ctx:  # type: Context
        await assert_write_permissions_from_raw_id(
            raw_id=project_id, configuration=configuration, context=ctx
        )
        response = await configuration.flux_client.delete_project(
            project_id=project_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        if purge:
            await delete_asset(
                raw_id=project_id, configuration=configuration, context=ctx
            )

        return response


@router.delete("/projects/{project_id}", summary="delete a project")
async def delete_project(
    request: Request,
    project_id: str,
    purge: bool = False,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await delete_project_impl(
            project_id=project_id, purge=purge, configuration=configuration, context=ctx
        )


@router.get(
    "/projects/{project_id}", response_model=Project, summary="retrieve a project"
)
async def get_project(
    request: Request,
    project_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=project_id, configuration=configuration, context=ctx
        )
        return await configuration.flux_client.get_project(
            project_id=project_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post("/projects/{project_id}", summary="post a project")
async def post_project(
    request: Request,
    project_id: str,
    project: Project,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_write_permissions_from_raw_id(
            raw_id=project_id, configuration=configuration, context=ctx
        )
        return await configuration.flux_client.update_project(
            project_id=project_id,
            body=project.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post("/projects/{project_id}/metadata", summary="edit metadata of a project")
async def post_metadata(
    request: Request,
    project_id: str,
    metadata_body: EditMetadata,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_write_permissions_from_raw_id(
            raw_id=project_id, configuration=configuration, context=ctx
        )
        return await configuration.flux_client.update_metadata(
            project_id=project_id,
            body=metadata_body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


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
    async with Context.start_ep(request=request) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=project_id, configuration=configuration, context=ctx
        )
        return await configuration.flux_client.get_metadata(
            project_id=project_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post(
    "/projects/{project_id}/duplicate",
    summary="duplicate a project",
    response_model=NewAssetResponse,
)
async def duplicate(
    request: Request,
    project_id: str,
    folder_id: str = Query(None, alias="folder-id"),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await asyncio.gather(
            assert_read_permissions_from_raw_id(
                raw_id=project_id, configuration=configuration, context=ctx
            ),
            assert_write_permissions_folder_id(folder_id=folder_id, context=ctx),
        )
        response = await configuration.flux_client.duplicate(
            project_id=project_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        asset = await configuration.assets_client.get_asset(
            encode_id(project_id), headers=ctx.headers()
        )
        metadata = {**asset, "name": f"{asset['name']} (copy)", "images": []}
        return await create_asset(
            request=request,
            kind="flux-project",
            raw_id=response["projectId"],
            raw_response=response,
            folder_id=folder_id,
            metadata=AssetMeta(**metadata),
            context=ctx,
            configuration=configuration,
        )


@router.post(
    "/projects/{project_id}/publish-application",
    response_model=NewAssetResponse,
    summary="retrieve records definition",
)
async def publish_application(
    request: Request,
    project_id: str,
    body: PublishApplicationBody,
    folder_id: str = Query(None, alias="folder-id"),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_write_permissions_from_raw_id(
            raw_id=project_id, configuration=configuration, context=ctx
        )
        package = await configuration.flux_client.publish_application(
            project_id=project_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        return await create_asset(
            request=request,
            kind="package",
            raw_id=package["id"],
            raw_response=package,
            folder_id=folder_id,
            metadata=AssetMeta(name=body.name),
            context=ctx,
            configuration=configuration,
        )
