import asyncio

from aiohttp import FormData
from fastapi import APIRouter, WebSocket, Depends, Request

from fastapi import HTTPException

from youwol.routers.upload.utils import create_borrowed_items, synchronize_permissions
from youwol.routers.commons import local_path, ensure_path
from youwol.context import Context
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.routers.upload.models import DataAssetStatus
from youwol.utils_low_level import start_web_socket, to_json
from youwol.web_socket import WebSocketsCache
from youwol.models import ActionStep

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.upload_data = ws
    await ws.send_json({})
    await start_web_socket(ws)


async def get_local_data(asset_id: str, raw_id: str, config: YouwolConfiguration):
    asset_gtw = config.localClients.assets_gateway_client

    data, access, metadata, raw_metadata = await asyncio.gather(
        asset_gtw.get_raw(kind='data', raw_id=raw_id),
        asset_gtw.get_asset_access(asset_id=asset_id),
        asset_gtw.get_asset_metadata(asset_id=asset_id),
        asset_gtw.get_raw_metadata(kind='data', raw_id=raw_id)
        )
    return data, access, metadata, raw_metadata


@router.post("/publish/{asset_id}", summary="upload a flux app")
async def publish(
        request: Request,
        asset_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_data)
    await context.web_socket.send_json({
        "assetId": asset_id,
        "status": str(DataAssetStatus.PROCESSING)
        })
    async with context.start(f"Upload Data") as ctx:

        tree_item = await config.localClients.assets_gateway_client.get_tree_item(item_id=asset_id)
        data, access, metadata, raw_metadata = await get_local_data(asset_id=asset_id, raw_id=tree_item['rawId'],
                                                                    config=config)
        form_data = FormData()
        form_data.add_field(name='file', value=data, filename=metadata['name'],
                            content_type=raw_metadata['contentType'])
        form_data.add_field('rawId', tree_item['rawId'])

        path_item = local_path(tree_item['treeId'], config=config)
        await ctx.info(
            step=ActionStep.RUNNING,
            content="Data retrieved",
            json={"path_item": to_json(path_item), "tree_item": tree_item}
            )

        assets_gtw_client = await config.get_assets_gateway_client(context=context)
        try:
            await assets_gtw_client.get_asset_metadata(asset_id=asset_id)
            await ctx.info(
                step=ActionStep.RUNNING,
                content="Data already found => update raw content (keep original file location)"
                )
            await assets_gtw_client.update_raw_asset(
                kind='data',
                raw_id=tree_item['rawId'],
                data=form_data,
                rest_of_path="content"
                )
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            await ctx.info(
                step=ActionStep.RUNNING,
                content="Data not already found => start creation"
                )
            await ensure_path(path_item=path_item, assets_gateway_client=assets_gtw_client)
            await assets_gtw_client.put_asset_with_raw(kind='data', folder_id=tree_item['folderId'], data=form_data)

        await create_borrowed_items(asset_id=asset_id, tree_id=tree_item['treeId'], assets_gtw_client=assets_gtw_client,
                                    context=ctx)
        await synchronize_permissions(assets_gtw_client=assets_gtw_client, asset_id=asset_id, context=context)

    return {}
