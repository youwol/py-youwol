import asyncio
import os
from pathlib import Path
from typing import List

from starlette.requests import Request

from fastapi import APIRouter, WebSocket, Depends, HTTPException
from pydantic import BaseModel

from youwol.services.backs.assets_gateway.utils import raw_id_to_asset_id
from youwol.routers.packages.utils import ensure_default_publish_location
from youwol.utils_low_level import start_web_socket
from youwol.configuration.youwol_configuration import yw_config, YouwolConfiguration
from youwol.context import Context
from youwol.models import ActionStep
from youwol.routers.download.messages import send_version_resolved, send_version_pending
from youwol.routers.upload.models import PackageStatus
from youwol.utils_paths import parse_json
from youwol.web_socket import WebSocketsCache

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.download_packages = ws
    await ws.send_json({})
    await start_web_socket(ws)


@router.get("/status",
            summary="execute action"
            )
async def status(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.download_packages)
    await context.info(ActionStep.STATUS, "Download Packages Status", {})
    return {}


@router.get("/groups",
            summary="execute action"
            )
async def groups(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.download_packages)
    assets_gtw = await config.get_assets_gateway_client(context)
    grps = await assets_gtw.get_groups()
    return grps['groups']


@router.get("/groups/{group_id}/drives",
            summary="execute action"
            )
async def drives(
        request: Request,
        group_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.download_packages)
    assets_gtw = await config.get_assets_gateway_client(context)
    resp = await assets_gtw.get_drives(group_id)
    return resp['drives']


class PackageVersion(BaseModel):
    rawId: str
    name: str
    version: str


class SyncMultipleBody(BaseModel):
    packages: List[PackageVersion]


@router.post("/synchronize",
             summary="download provided packages"
             )
async def synchronize(
        request: Request,
        body: SyncMultipleBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    queue = asyncio.Queue()
    for package in body.packages:
        queue.put_nowait(package)

    async def worker(_queue):
        while True:
            target = await _queue.get()
            await download(request=request, package=target, config=config)
            queue.task_done()

    tasks = []
    for i in range(5):
        task = asyncio.get_event_loop().create_task(worker(queue))
        tasks.append(task)

    await queue.join()

    for task in tasks:
        task.cancel()

    return {}


async def download(request: Request, package: PackageVersion, config: YouwolConfiguration):

    async def publish_cdn_only(cdn_pack):
        zip_path = Path('./') / "tmp_zips" / f'{package.rawId}.zip'
        try:
            with open(zip_path, 'wb') as file:
                file.write(cdn_pack)
            await config.localClients.cdn_client.publish(zip_path=zip_path)
        finally:
            os.remove(zip_path)

    context = Context(config=config, request=request, web_socket=WebSocketsCache.download_packages)

    async with context.start("Download package") as ctx:
        await send_version_pending(raw_id=package.rawId, name=package.name, version=package.version, context=ctx)
        assets_gateway = await config.get_assets_gateway_client(context=ctx)
        pack = await assets_gateway.cdn_get_package(library_name=package.name, version=package.version)
        await ctx.info(step=ActionStep.STATUS, content=f"successfully got .zip package for {package.name}", json={})

        try:
            client = config.localClients.assets_gateway_client
            asset_id = raw_id_to_asset_id(package.rawId)
            asset = await client.get_asset_metadata(asset_id=asset_id)
            await ctx.info(step=ActionStep.STATUS, content=f"{package.name}: asset already exists",
                           json=asset)
            await publish_cdn_only(pack)
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            client = config.localClients.assets_gateway_client
            folder_id = await ensure_default_publish_location(context)
            await ctx.info(step=ActionStep.STATUS, content=f"{package.name}: asset does not exists, create it", json={})
            await client.put_asset_with_raw(kind='package', folder_id=folder_id, data={'file': pack})

        await ctx.info(step=ActionStep.STATUS, content=f"successfully published {package.name}", json={})

        await send_version_resolved(raw_id=package.rawId, name=package.name, version=package.version,
                                    status=PackageStatus.SYNC, context=ctx)


@router.get("/info/{raw_id}")
async def package_info(
        request: Request,
        raw_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    ctx = Context(config=config, request=request, web_socket=WebSocketsCache.download_packages)
    assets_gtw = await config.get_assets_gateway_client(ctx)
    resp = await assets_gtw.get_raw_metadata(kind='package', raw_id=raw_id)
    loading_graph = await assets_gtw.cdn_loading_graph(body={"libraries": {resp['name']: "latest",
                                                                           '@youwol/flux-core': "latest"}})
    cdn_db = parse_json(config.pathsBook.local_cdn_docdb)
    data = {f"{r['library_id']}" for r in cdn_db['documents']}

    def item_status(r):
        return PackageStatus.SYNC if f"{r['name']}#{r['version']}" in data else PackageStatus.NOT_FOUND

    await asyncio.gather(*[
        send_version_resolved(raw_id=r["id"], name=r['name'], version=r['version'], status=item_status(r), context=ctx)
        for r in loading_graph['lock']
        ])

    return {}
