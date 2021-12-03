import base64
import json

from fastapi import APIRouter, WebSocket, Depends, Request

from fastapi import HTTPException

from youwol.routers.commons import ensure_path, remote_path
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
    WebSocketsCache.download_flux_apps = ws
    await ws.send_json({})
    await start_web_socket(ws)


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def encode_id(raw_id: str) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


@router.post("/publish/{asset_id}", summary="upload a flux app")
async def publish(
        request: Request,
        asset_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.download_flux_apps)
    await context.web_socket.send_json({
        "assetId": asset_id,
        "status": str(FluxAppStatus.PROCESSING)
        })
    async with context.start(f"Upload flux app") as ctx:

        assets_gtw_client = await config.get_assets_gateway_client(context=context)
        raw_id = decode_id(asset_id)
        flux_app = await assets_gtw_client.get_raw(kind='flux-project', raw_id=raw_id)
        flux_app = json.loads(flux_app.decode("utf-8"))
        tree_item = await assets_gtw_client.get_tree_item(item_id=asset_id)
        path_item = await remote_path(tree_item=tree_item, context=context)
        await ctx.info(
            step=ActionStep.RUNNING,
            content="Data retrieved",
            json={"path_item": to_json(path_item), "flux-app": flux_app}
            )
        local_assets_gtw = config.localClients.assets_gateway_client
        try:
            await local_assets_gtw.get_asset_metadata(asset_id=asset_id)
            await ctx.info(
                step=ActionStep.RUNNING,
                content="Project already found => update raw content only"
                )
            await config.localClients.flux_client.update_project(project_id=raw_id, body=flux_app)
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            await ctx.info(
                step=ActionStep.RUNNING,
                content="Project not already found => start creation"
                )

            await ensure_path(path_item=path_item, assets_gateway_client=local_assets_gtw)
            # The next line is somehow a patch that will allow to create a project from existing data
            flux_app['projectId'] = raw_id
            # The next line is a hack because sometimes the name of the flux project is not the name of the tree item
            # It should depends on how the renaming is done
            # https://www.notion.so/youwol/flux-project-name-tree-item-name-not-in-sync-10019aecefbe4ad5a04a5def756ddccd
            flux_app['name'] = tree_item['name']
            await local_assets_gtw.put_asset_with_raw(
                kind='flux-project',
                folder_id=tree_item['folderId'],
                data=json.dumps(flux_app).encode()
                )
        finally:
            await context.web_socket.send_json({
                "assetId": asset_id,
                "status": str(FluxAppStatus.DONE)
                })

    return {}
