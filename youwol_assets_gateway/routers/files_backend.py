from aiohttp import ClientResponse
from fastapi import APIRouter, Depends, Query
from starlette.requests import Request
from starlette.responses import Response

from youwol_assets_gateway.raw_stores import AssetMeta, AssetImg
from youwol_assets_gateway.routers.common import assert_write_permissions_folder_id, create_asset, \
    assert_read_permissions_from_raw_id

from youwol_utils.context import Context
from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.http_clients.assets_gateway import NewAssetResponse
from youwol_utils.http_clients.files_backend import GetInfoResponse, PostFileResponse, PostMetadataBody

router = APIRouter(tags=["assets-gateway.files-backend"])


mime_types_images = ["image/png", "image/jpeg", "image/gif", "image/bmp", "image/x-icon", "image/tiff",
                     "image/webp", "image/svg+xml"]


@router.get("/healthz")
async def healthz(request: Request, configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        return await configuration.files_client.healthz(headers=ctx.headers())


@router.post(
    "/files",
    response_model=NewAssetResponse,
    summary="create a new file"
)
async def upload(
        request: Request,
        folder_id: str = Query(None, alias="folder-id"),
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        form = await request.form()
        content = await form.get('file').read()
        form = {
            'file': content,
            'content_type': form.get('content_type', ''),
            'content_encoding': form.get('content_encoding', ''),
            'file_id': form.get('file_id', ''),
            'file_name': form.get('file_name', '')
        }
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        file = PostFileResponse(
            **await configuration.files_client.upload(
                data=form,
                headers=ctx.headers()
            )
        )
        images = [AssetImg(name=file.fileName, content=content)] \
            if file.contentType in mime_types_images else \
            []
        return await create_asset(
            kind="package",
            raw_id=file.fileId,
            raw_response=file.dict(),
            folder_id=folder_id,
            metadata=AssetMeta(name=file.fileName, images=images),
            context=ctx,
            configuration=configuration
        )


@router.get(
    "/files/{file_id}/info",
    response_model=GetInfoResponse,
    summary="get file information"
)
async def get_stats(
        request: Request,
        file_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(raw_id=file_id, configuration=configuration, context=ctx)
        return await configuration.files_client.get_info(
            file_id=file_id,
            headers=ctx.headers()
        )


@router.post(
    "/files/{file_id}/metadata",
    summary="update file metadata"
)
async def update_metadata(
        request: Request,
        file_id: str,
        body: PostMetadataBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(raw_id=file_id, configuration=configuration, context=ctx)
        return await configuration.files_client.update_metadata(
            file_id=file_id,
            body=body.dict(),
            headers=ctx.headers()
        )


@router.get(
    "/files/{file_id}",
    summary="get file content"
)
async def get_file(
        request: Request,
        file_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async def reader(resp: ClientResponse):
        resp_bytes = await resp.read()
        return Response(content=resp_bytes, headers={k: v for k, v in resp.headers.items()})

    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(raw_id=file_id, configuration=configuration, context=ctx)
        response = await configuration.files_client.get(
            file_id=file_id,
            reader=reader,
            headers=ctx.headers()
        )
        return response


@router.delete(
    "/files/{file_id}",
    summary="remove a file"
)
async def remove_file(
        request: Request,
        file_id: str,
        configuration: Configuration = Depends(get_configuration)
):

    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(raw_id=file_id, configuration=configuration, context=ctx)
        response = await configuration.files_client.remove(
            file_id=file_id,
            headers=ctx.headers()
        )
        return response
