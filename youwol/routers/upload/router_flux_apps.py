import base64
import json

from fastapi import APIRouter, WebSocket, Depends, Request

from fastapi import HTTPException

from youwol.routers.upload.shared_utils import local_path, ensure_path
from youwol.context import Context
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.routers.upload.models import FluxAppStatus
from youwol.utils_low_level import start_web_socket, to_json
from youwol.web_socket import WebSocketsCache
from youwol.models import ActionStep
router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.upload_flux_apps = ws
    await ws.send_json({})
    await start_web_socket(ws)


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def encode_id(raw_id: str) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


async def get_local_flux_app(raw_id: str, config: YouwolConfiguration):

    flux_client = config.localClients.flux_client
    project = await flux_client.get_project(raw_id)
    return project


@router.post("/publish/{asset_id}", summary="upload a flux app")
async def publish(
        request: Request,
        asset_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_flux_apps)
    await context.web_socket.send_json({
        "assetId": asset_id,
        "status": str(FluxAppStatus.PROCESSING)
        })
    async with context.start(f"Upload flux app") as ctx:

        raw_id = decode_id(asset_id)
        local_flux_app = await get_local_flux_app(raw_id=raw_id, config=config)
        tree_item = await config.localClients.assets_gateway_client.get_tree_item(item_id=asset_id)
        path_item = local_path(tree_item['treeId'], config=config)
        await ctx.info(
            step=ActionStep.RUNNING,
            content="Data retrieved",
            json={"path_item": to_json(path_item), "flux-app": local_flux_app}
            )

        assets_gtw_client = await config.get_assets_gateway_client(context=context)

        try:
            await assets_gtw_client.get_asset_metadata(asset_id=asset_id)
            await ctx.info(
                step=ActionStep.RUNNING,
                content="Project already found => update raw content only"
                )
            flux_client = await config.get_flux_client(context=context)
            await flux_client.update_project(project_id=raw_id, body=local_flux_app)
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            await ctx.info(
                step=ActionStep.RUNNING,
                content="Project not already found => start creation"
                )

            await ensure_path(path_item=path_item, assets_gateway_client=assets_gtw_client)
            local_flux_app['projectId'] = raw_id
            await assets_gtw_client.put_asset_with_raw(
                kind='flux-project',
                folder_id=tree_item['folderId'],
                data=json.dumps(local_flux_app).encode()
                )
        finally:
            await context.web_socket.send_json({
                "assetId": asset_id,
                "status": str(FluxAppStatus.DONE)
                })

    return {}
