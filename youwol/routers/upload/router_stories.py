import base64
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, WebSocket, Depends, Request

from utils_paths import parse_json, write_json
from youwol.routers.upload.utils import synchronize_permissions_metadata_symlinks
from youwol.routers.commons import local_path, ensure_path
from youwol.context import Context
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.routers.upload.models import StoryStatus
from youwol.utils_low_level import start_web_socket, to_json
from youwol.web_socket import WebSocketsCache
from youwol.models import ActionStep
router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.upload_stories = ws
    await ws.send_json({})
    await start_web_socket(ws)


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def zip_local_story(raw_id: str, config: YouwolConfiguration) -> bytes:
    stories = parse_json(config.pathsBook.local_stories_docdb)
    documents = parse_json(config.pathsBook.local_stories_documents_docdb)
    data = {
        "story": next(d for d in stories['documents'] if d['story_id'] == raw_id),
        "documents": [d for d in documents['documents'] if d['story_id'] == raw_id]
        }

    with tempfile.TemporaryDirectory() as tmp_folder:
        base_path = Path(tmp_folder)
        write_json(data=data, path=base_path / 'data.json')
        storage_stories = config.pathsBook.local_stories_storage
        for doc in data['documents']:
            shutil.copy(storage_stories / doc['content_id'], base_path / doc['content_id'])

        zipper = zipfile.ZipFile(base_path / 'story.zip', 'w', zipfile.ZIP_DEFLATED)
        for filename in ['data.json'] + [doc['content_id'] for doc in data['documents']]:
            zipper.write(base_path / filename, arcname=filename)
        zipper.close()
        return (Path(tmp_folder) / "story.zip").read_bytes()


@router.post("/publish/{asset_id}", summary="upload a story")
async def publish(
        request: Request,
        asset_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_stories)

    async with context.start(
            f"Upload story",
            on_enter=lambda _ctx: _ctx.web_socket.send_json({
                "assetId": asset_id,
                "status": str(StoryStatus.PROCESSING)
                }),
            on_exit=lambda _ctx: _ctx.web_socket.send_json({
                "assetId": asset_id,
                "status": str(StoryStatus.DONE)
                }),
            ) as ctx:

        raw_id = decode_id(asset_id)
        tree_item = await config.localClients.assets_gateway_client.get_tree_item(item_id=asset_id)
        path_item = local_path(tree_item['treeId'], config=config)
        await ctx.info(
            step=ActionStep.RUNNING,
            content="Data retrieved",
            json={"path_item": to_json(path_item)}
            )

        assets_gtw_client = await config.get_assets_gateway_client(context=context)
        # assets_gtw_client = context.config.localClients.assets_gateway_client
        await ensure_path(path_item=path_item, assets_gateway_client=assets_gtw_client)
        zip_content = zip_local_story(raw_id=raw_id, config=config)
        await assets_gtw_client.put_asset_with_raw(
            kind='story',
            folder_id=path_item.folders[0].folderId,
            data={'file': zip_content, 'content_encoding': 'identity'},
            rest_of_path="/publish"
            )
        await synchronize_permissions_metadata_symlinks(
            asset_id=asset_id,
            tree_id=tree_item['treeId'],
            assets_gtw_client=assets_gtw_client,
            context=ctx
            )

    return {}
