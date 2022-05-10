from aiohttp import ClientResponse
from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.context import Context
from youwol_utils.http_clients.assets_backend import HealthzResponse, AssetResponse, NewAssetBody, PostAssetBody, \
    AccessPolicyBody, AccessPolicyResp, PermissionsResp, AccessInfoResp

router = APIRouter(tags=["assets-gateway.flux-backend"])


@router.get("/healthz",
            summary="return status of the service",
            response_model=HealthzResponse)
async def healthz(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.healthz(
            headers=ctx.headers()
        )


@router.put("/assets",
            response_model=AssetResponse,
            summary="new asset")
async def create_asset(
        request: Request,
        body: NewAssetBody,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.create_asset(
            body=body.dict(),
            headers=ctx.headers()
        )


@router.post("/assets/{asset_id}",
             response_model=AssetResponse,
             summary="update an asset"
             )
async def post_asset(
        request: Request,
        asset_id: str,
        body: PostAssetBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.update_asset(
            asset_id=asset_id,
            body=body.dict(),
            headers=ctx.headers()
        )


@router.delete("/assets/{asset_id}", summary="delete an asset")
async def delete_asset(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.delete_asset(
            asset_id=asset_id,
            headers=ctx.headers()
        )


@router.get("/assets/{asset_id}",
            response_model=AssetResponse,
            summary="return an asset")
async def get_asset(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.get_asset(
            asset_id=asset_id,
            headers=ctx.headers()
        )


@router.put("/assets/{asset_id}/access/{group_id}",
            summary="update an asset")
async def put_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        body: AccessPolicyBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.put_access_policy(
            asset_id=asset_id,
            group_id=group_id,
            body=body.dict(),
            headers=ctx.headers()
        )


@router.delete("/assets/{asset_id}/access/{group_id}", summary="update an asset")
async def delete_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.delete_access_policy(
            asset_id=asset_id,
            group_id=group_id,
            headers=ctx.headers()
        )


@router.get("/assets/{asset_id}/access/{group_id}",
            response_model=AccessPolicyResp,
            summary="update an asset")
async def get_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.get_access_policy(
            asset_id=asset_id,
            group_id=group_id,
            headers=ctx.headers()
        )


@router.get("/assets/{asset_id}/permissions",
            response_model=PermissionsResp,
            summary="permissions of the user on the asset")
async def get_permissions(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.get_permissions(
            asset_id=asset_id,
            headers=ctx.headers()
        )


@router.get("/assets/{asset_id}/access-info",
            response_model=AccessInfoResp,
            summary="permissions of the user on the asset")
async def get_permissions(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.get_access_info(
            asset_id=asset_id,
            headers=ctx.headers()
        )


@router.post("/assets/{asset_id}/images/{filename}", summary="add an image to asset")
async def post_image(
        request: Request,
        asset_id: str,
        filename: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        form = await request.form()
        src = await form.get('file').read()
        return await configuration.assets_client.post_image(
            asset_id=asset_id,
            filename=filename,
            src=src,
            headers=ctx.headers()
        )


@router.delete("/assets/{asset_id}/images/{filename}", summary="remove an image")
async def remove_image(
        request: Request,
        asset_id: str,
        filename: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.remove_image(
            asset_id=asset_id,
            filename=filename,
            headers=ctx.headers()
        )


@router.get("/assets/{asset_id}/{media_type}/{name}", summary="return a media")
async def get_media(
        request: Request,
        asset_id: str,
        media_type: str,
        name: str,
        configuration: Configuration = Depends(get_configuration)
):
    async def reader(resp: ClientResponse):
        resp_bytes = await resp.read()
        return Response(content=resp_bytes, headers={k: v for k, v in resp.headers.items()})

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.assets_client.get_media(
            asset_id=asset_id,
            media_type=media_type,
            name=name,
            reader=reader,
            headers=ctx.headers()
        )
