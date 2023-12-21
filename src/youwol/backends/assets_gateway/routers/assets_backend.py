# standard library
import uuid

# typing
from typing import Optional

# third parties
from aiohttp import ClientResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.assets_gateway.configurations import (
    Configuration,
    get_configuration,
)

# Youwol utilities
from youwol.utils import (
    aiohttp_to_starlette_response,
    ensure_group_permission,
    private_group_id,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend import (
    AccessInfoResp,
    AccessPolicyBody,
    AccessPolicyResp,
    AssetResponse,
    HealthzResponse,
    PermissionsResp,
    PostAssetBody,
)
from youwol.utils.http_clients.assets_gateway import NewAssetResponse

# relative
from ..utils import AssetMeta
from .common import create_asset as common_create_asset

router = APIRouter(tags=["assets-gateway.flux-backend"])


class NewEmptyAssetBody(BaseModel):
    rawId: Optional[str]
    kind: str
    name: str = ""
    description: str = ""
    tags: list[str] = []


@router.get(
    "/healthz", summary="return status of the service", response_model=HealthzResponse
)
async def healthz(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.assets_client.healthz(
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys)
        )


@router.put("/assets", response_model=NewAssetResponse, summary="new asset")
async def create_asset(
    request: Request,
    body: NewEmptyAssetBody,
    folder_id: str = Query(None, alias="folder-id"),
    configuration: Configuration = Depends(get_configuration),
) -> NewAssetResponse:
    """
    Creates an asset not affiliated to any backends; for files and packages kind of assets, use the dedicated endpoints
    [upload](@yw-nav-func:youwol.backends.assets_gateway.routers.files_backend.upload)
    [publish_library](@yw-nav-func:youwol.backends.assets_gateway.routers.cdn_backend.publish_library)
    respectively.

    The asset can be populated with files afterward.

    Parameters:
        request: Incoming request.
        body: Asset description.
        folder_id: Folder ID (from files explorer) in which the asset is located in the file explorer.
            If not provided, use the 'downloadFolder' of the user's
            [default drive](@yw-nav-class:youwol.backends.tree_db.root_paths.get_default_user_drive).
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.assets_gateway.configurations.Configuration).

    Return:
        New asset description (no `rawResponse` associated).
    """
    # This end point create an asset not affiliated to any backends.
    # It can be populated with files afterward.
    # For asset creation related to a backend, see specific router for this backend in the current directory.
    async with Context.start_ep(request=request) as ctx:
        raw_id = body.rawId or str(uuid.uuid4())
        if not folder_id:
            await ctx.info(
                text="No folder specified to create the asset, use user's download folder."
            )
            user = user_info(request)
            default_drive = await configuration.treedb_client.get_default_drive(
                group_id=private_group_id(user), headers=ctx.headers()
            )
            folder_id = default_drive["downloadFolderId"]
        await ctx.info(text="Create un-affiliated asset", data={"folderId": folder_id})
        return await common_create_asset(
            request=request,
            kind=body.kind,
            raw_id=raw_id,
            raw_response={},
            folder_id=folder_id,
            metadata=AssetMeta(
                name=body.name, description=body.description, tags=body.tags
            ),
            context=ctx,
            configuration=configuration,
        )


@router.post("/assets/{asset_id}/files")
async def post_asset_files(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.add_zip_files](@yw-nav-func:youwol.backends.assets.root_paths.add_zip_files)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        assets_db = configuration.assets_client
        permissions = await assets_db.get_permissions(
            asset_id=asset_id, headers=ctx.headers()
        )
        if not permissions["write"]:
            raise HTTPException(
                status_code=403, detail=f"Unauthorized to write asset {asset_id}"
            )

        form = await request.form()
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise ValueError("Field `file` of form is not of type `UploadFile`")
        data = await file.read()
        return await assets_db.add_zip_files(
            asset_id=asset_id,
            data=data,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get("/assets/{asset_id}/files/{rest_of_path:path}")
async def get_file(
    request: Request,
    asset_id: str,
    rest_of_path: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.get_file](@yw-nav-func:youwol.backends.assets.root_paths.get_file)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        assets_db = configuration.assets_client
        permissions = await assets_db.get_permissions(
            asset_id=asset_id, headers=ctx.headers()
        )
        if not permissions["read"]:
            raise HTTPException(
                status_code=403, detail=f"Unauthorized to read asset {asset_id}"
            )

        return await assets_db.get_file(
            asset_id=asset_id,
            path=rest_of_path,
            custom_reader=aiohttp_to_starlette_response,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/assets/{asset_id}/files")
async def delete_files(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.delete_files](@yw-nav-func:youwol.backends.assets.root_paths.delete_files)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        assets_db = configuration.assets_client
        permissions = await assets_db.get_permissions(
            asset_id=asset_id, headers=ctx.headers()
        )
        if not permissions["write"]:
            raise HTTPException(
                status_code=403, detail=f"Unauthorized to delete asset {asset_id}"
            )

        return await assets_db.delete_files(
            asset_id=asset_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get("/assets/{asset_id}/files")
async def zip_all_files(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.get_zip_files](@yw-nav-func:youwol.backends.assets.root_paths.get_zip_files)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        assets_db = configuration.assets_client
        permissions = await assets_db.get_permissions(
            asset_id=asset_id, headers=ctx.headers()
        )
        if not permissions["read"]:
            raise HTTPException(
                status_code=403, detail=f"Unauthorized to read asset {asset_id}"
            )

        content = await assets_db.get_zip_files(
            asset_id=asset_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        return Response(content=content, media_type="application/zip")


@router.post(
    "/assets/{asset_id}", response_model=AssetResponse, summary="update an asset"
)
async def post_asset(
    request: Request,
    asset_id: str,
    body: PostAssetBody,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.post_asset](@yw-nav-func:youwol.backends.assets.root_paths.post_asset)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        asset = await configuration.assets_client.get_asset(
            asset_id=asset_id, headers=ctx.headers()
        )
        if body.groupId:
            ensure_group_permission(request=request, group_id=body.groupId)

        ensure_group_permission(request=request, group_id=asset["groupId"])

        return await configuration.assets_client.update_asset(
            asset_id=asset_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/assets/{asset_id}", summary="delete an asset")
async def delete_asset(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.delete_asset](@yw-nav-func:youwol.backends.assets.root_paths.delete_asset)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        asset = await configuration.assets_client.get_asset(
            asset_id=asset_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=asset["groupId"])

        return await configuration.assets_client.delete_asset(
            asset_id=asset_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/assets/{asset_id}", response_model=AssetResponse, summary="return an asset"
)
async def get_asset(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.get_asset](@yw-nav-func:youwol.backends.assets.root_paths.get_asset)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        return await configuration.assets_client.get_asset(
            asset_id=asset_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.put("/assets/{asset_id}/access/{group_id}", summary="update an asset")
async def put_access_policy(
    request: Request,
    asset_id: str,
    group_id: str,
    body: AccessPolicyBody,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.put_access_policy](@yw-nav-func:youwol.backends.assets.root_paths.put_access_policy)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        asset = await configuration.assets_client.get_asset(
            asset_id=asset_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=asset["groupId"])

        return await configuration.assets_client.put_access_policy(
            asset_id=asset_id,
            group_id=group_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/assets/{asset_id}/access/{group_id}", summary="update an asset")
async def delete_access_policy(
    request: Request,
    asset_id: str,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.delete_access_policy](@yw-nav-func:youwol.backends.assets.root_paths.delete_access_policy)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        asset = await configuration.assets_client.get_asset(
            asset_id=asset_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=asset["groupId"])

        return await configuration.assets_client.delete_access_policy(
            asset_id=asset_id,
            group_id=group_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/assets/{asset_id}/access/{group_id}",
    response_model=AccessPolicyResp,
    summary="update an asset",
)
async def get_access_policy(
    request: Request,
    asset_id: str,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.get_access_policy](@yw-nav-func:youwol.backends.assets.root_paths.get_access_policy)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        return await configuration.assets_client.get_access_policy(
            asset_id=asset_id,
            group_id=group_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/assets/{asset_id}/permissions",
    response_model=PermissionsResp,
    summary="permissions of the user on the asset",
)
async def get_permissions(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.get_permissions](@yw-nav-func:youwol.backends.assets.root_paths.get_permissions)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        return await configuration.assets_client.get_permissions(
            asset_id=asset_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/assets/{asset_id}/access-info",
    response_model=AccessInfoResp,
    summary="permissions of the user on the asset",
)
async def get_access_info(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.access_info](@yw-nav-func:youwol.backends.assets.root_paths.access_info)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        return await configuration.assets_client.get_access_info(
            asset_id=asset_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post("/assets/{asset_id}/images/{filename}", summary="add an image to asset")
async def post_image(
    request: Request,
    asset_id: str,
    filename: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.post_image](@yw-nav-func:youwol.backends.assets.root_paths.post_image)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        asset = await configuration.assets_client.get_asset(
            asset_id=asset_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=asset["groupId"])

        form = await request.form()
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise ValueError("Field `file` of form is not of type `UploadFile`")
        src = await file.read()
        return await configuration.assets_client.post_image(
            asset_id=asset_id,
            filename=filename,
            src=src,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/assets/{asset_id}/images/{filename}", summary="remove an image")
async def remove_image(
    request: Request,
    asset_id: str,
    filename: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.remove_image](@yw-nav-func:youwol.backends.assets.root_paths.remove_image)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """
    async with Context.start_ep(request=request) as ctx:
        asset = await configuration.assets_client.get_asset(
            asset_id=asset_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=asset["groupId"])

        return await configuration.assets_client.remove_image(
            asset_id=asset_id,
            filename=filename,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get("/assets/{asset_id}/{media_type}/{name}", summary="return a media")
async def get_media(
    request: Request,
    asset_id: str,
    media_type: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [assets.get_media_image](@yw-nav-func:youwol.backends.assets.root_paths.get_media_image) or
    [assets.get_media_thumbnail](@yw-nav-func:youwol.backends.assets.root_paths.get_media_thumbnail)
    (depending on `media_type`)
    of [assets](@yw-nav-mod:youwol.backends.assets) service.
    """

    async def reader(resp: ClientResponse):
        resp_bytes = await resp.read()
        return Response(content=resp_bytes, headers=dict(resp.headers.items()))

    async with Context.start_ep(request=request) as ctx:
        return await configuration.assets_client.get_media(
            asset_id=asset_id,
            media_type=media_type,
            name=name,
            reader=reader,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
