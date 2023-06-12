# third parties
from aiohttp import ClientResponse
from fastapi import APIRouter, Depends, HTTPException, Query
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
    create_asset,
    delete_asset,
)
from youwol.backends.assets_gateway.utils import (
    AssetImg,
    AssetMeta,
    raw_id_to_asset_id,
    to_asset_resp,
)

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_gateway import (
    NewAssetResponse,
    PermissionsResponse,
)
from youwol.utils.http_clients.files_backend import (
    GetInfoResponse,
    PostFileResponse,
    PostMetadataBody,
)

router = APIRouter(tags=["assets-gateway.files-backend"])


mime_types_images = [
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/bmp",
    "image/x-icon",
    "image/tiff",
    "image/webp",
    "image/svg+xml",
]


@router.get("/healthz")
async def healthz(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await configuration.files_client.healthz(
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys)
        )


@router.post("/files", response_model=NewAssetResponse, summary="create a new file")
async def upload(
    request: Request,
    folder_id: str = Query(None, alias="folder-id"),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, muted_http_errors={404}
    ) as ctx:  # type: Context
        form = await request.form()
        content = await form.get("file").read()
        form = {
            "file": content,
            "content_type": form.get("content_type", ""),
            "content_encoding": form.get("content_encoding", ""),
            "file_id": form.get("file_id", ""),
            "file_name": form.get("file_name", ""),
        }
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        file = PostFileResponse(
            **await configuration.files_client.upload(
                data=form,
                headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
            )
        )
        try:
            asset = await configuration.assets_client.get(
                asset_id=raw_id_to_asset_id(file.fileId), headers=ctx.headers()
            )
            response = NewAssetResponse(
                **{
                    **to_asset_resp(
                        asset,
                        permissions=PermissionsResponse(
                            read=True, write=True, share=True
                        ),
                    ).dict(),
                    "itemId": asset["assetId"],
                    "rawResponse": file,
                }
            )
            return response
        except HTTPException as e:
            if e.status_code != 404:
                raise e
        if not folder_id:
            raise ValueError(
                "When uploading a new file, parent folder's id should be supplied."
            )

        images = (
            [AssetImg(name=file.fileName, content=content)]
            if file.contentType in mime_types_images
            else []
        )
        parameters_base = {
            "request": request,
            "kind": "data",
            "raw_id": file.fileId,
            "raw_response": file.dict(),
            "folder_id": folder_id,
            "context": ctx,
            "configuration": configuration,
        }
        try:
            return await create_asset(
                **parameters_base, metadata=AssetMeta(name=file.fileName, images=images)
            )
        except HTTPException:
            # create_asset may fail because of images, e.g. some PIL decoding particular images format
            return await create_asset(
                **parameters_base, metadata=AssetMeta(name=file.fileName)
            )


@router.get(
    "/files/{file_id}/info",
    response_model=GetInfoResponse,
    summary="get file information",
)
async def get_stats(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(
            raw_id=file_id, configuration=configuration, context=ctx
        )
        return await configuration.files_client.get_info(
            file_id=file_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post("/files/{file_id}/metadata", summary="update file metadata")
async def update_metadata(
    request: Request,
    file_id: str,
    body: PostMetadataBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(
            raw_id=file_id, configuration=configuration, context=ctx
        )
        return await configuration.files_client.update_metadata(
            file_id=file_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get("/files/{file_id}", summary="get file content")
async def get_file(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async def reader(resp: ClientResponse):
        resp_bytes = await resp.read()
        return Response(content=resp_bytes, headers=dict(resp.headers.items()))

    async with Context.start_ep(request=request) as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(
            raw_id=file_id, configuration=configuration, context=ctx
        )
        response = await configuration.files_client.get(
            file_id=file_id,
            reader=reader,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        return response


async def remove_file_impl(
    file_id: str, purge: bool, configuration: Configuration, context: Context
):
    async with context.start(action="remove_file_impl") as ctx:  # type: Context
        await assert_read_permissions_from_raw_id(
            raw_id=file_id, configuration=configuration, context=ctx
        )
        response = await configuration.files_client.remove(
            file_id=file_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        if purge:
            await delete_asset(raw_id=file_id, configuration=configuration, context=ctx)

        return response


@router.delete("/files/{file_id}", summary="remove a file")
async def remove_file(
    request: Request,
    file_id: str,
    purge: bool = False,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await remove_file_impl(
            file_id=file_id, purge=purge, configuration=configuration, context=ctx
        )
