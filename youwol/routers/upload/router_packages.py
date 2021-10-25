import asyncio
import base64
import json
from collections import defaultdict
from itertools import groupby
from pathlib import Path
from typing import List, Any

from starlette.requests import Request
from fastapi import HTTPException

from fastapi import APIRouter, WebSocket, Depends

from youwol.routers.upload.utils import synchronize_permissions_metadata_symlinks
from youwol.routers.commons import ensure_path, local_path
from youwol.context import Context
from youwol.models import ActionStep
from youwol.routers.packages.utils import get_all_packages
from youwol.routers.upload.messages import (
    send_package_pending, send_version_pending, send_version_resolved,
    send_package_resolved,
    )
from youwol.routers.upload.models import Library, Release, PathResp, PackageStatus, SyncMultipleBody, LibrariesList, \
    TreeItem
from youwol.utils_low_level import to_json, start_web_socket
from youwol_utils import to_group_scope
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient

from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.utils_paths import parse_json
from youwol.services.backs.cdn.utils import to_package_name

from youwol.web_socket import WebSocketsCache
router = APIRouter()


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def encode_id(raw_id: str) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


def get_local_package(asset_id: str, config: YouwolConfiguration) -> Library:
    """
    Not populated with tree items
    """
    data_packages = parse_json(config.pathsBook.local_docdb / "cdn" / "libraries" / "data.json")
    raw_id = decode_id(asset_id)
    library_name = decode_id(raw_id)
    releases = [d for d in data_packages['documents'] if d['library_name'] == library_name]
    if not releases:
        raise HTTPException(status_code=404, detail=f'Local package {library_name} not found')

    return Library(
        libraryName=library_name,
        namespace=releases[0]["namespace"],
        releases=[Release(version=r['version'], fingerprint=r['fingerprint'] if 'fingerprint' in r else '')
                  for r in releases],
        assetId=asset_id,
        rawId=raw_id,
        treeItems=[],
        )


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.upload_packages = ws
    await ws.send_json({})
    await start_web_socket(ws)


@router.get("/{tree_id}/remote-path",
            summary="return the remote path of the tree item",
            response_model=PathResp)
async def remote_path(
        request: Request,
        tree_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ) -> PathResp:

    async def path_rec(current_folder) -> (List[str], List[str]):

        folder, drive = await asyncio.gather(
            client.get_tree_folder(folder_id=current_folder),
            client.get_tree_drive(drive_id=current_folder),
            return_exceptions=True
            )
        if isinstance(drive, dict):
            return [drive['name']], [drive['driveId']]
        parent = await path_rec(folder['parentFolderId'])
        return parent[0] + [folder['name']], parent[1] + [folder['folderId']]

    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_packages)
    client = await config.get_assets_gateway_client(context)
    tree_item = await client.get_tree_item(item_id=tree_id)
    names_path, ids_path = await path_rec(tree_item['folderId'])

    return PathResp(
        group=to_group_scope(tree_item['groupId']),
        drive=await client.get_tree_drive(drive_id=ids_path[0]),
        folders=[{"name": name} for name in names_path[1:]] if names_path else []
        )


@router.get("/{tree_id}/path",
            summary="execute action",
            response_model=PathResp)
async def path(tree_id: str,
               config: YouwolConfiguration = Depends(yw_config)) -> PathResp:

    return local_path(tree_id=tree_id, config=config)


async def delete_library_version_generic(
        request: Request,
        asset_id: str,
        version: str,
        config: YouwolConfiguration = Depends(yw_config)):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_packages)
    library_name = to_package_name(to_package_name(asset_id))
    local_package = get_local_package(asset_id=asset_id, config=config)

    async with context.start(f"Delete {library_name}#{version}") as ctx:
        await asyncio.gather(
            send_version_pending(asset_id=asset_id, name=library_name, version=version, context=ctx),
            send_package_pending(package=local_package, context=ctx)
            )

        local_cdn = config.localClients.cdn_client
        assets_gateway = await config.get_assets_gateway_client(context)

        local_resp, remote_resp = await asyncio.gather(
            local_cdn.delete_version(library_name=library_name, version=version),
            assets_gateway.cdn_delete_version(library_name=library_name, version=version),
            return_exceptions=True
            )
        if isinstance(local_resp, Exception):
            raise local_resp

        if isinstance(remote_resp, Exception):
            raise remote_resp

        await check_package_status(package=local_package, context=context)
        return {}


@router.delete("/remove/{asset_id}/{version}", summary="execute action")
async def delete_library_version(
        request: Request,
        asset_id: str,
        version: str,
        config: YouwolConfiguration = Depends(yw_config)):

    return await delete_library_version_generic(request=request, asset_id=asset_id, version=version, config=config)


@router.post("/register-asset/{asset_id}", summary="execute action")
async def register_asset(
        request: Request,
        asset_id: str,
        config: YouwolConfiguration = Depends(yw_config)):

    local_cdn = config.localClients.cdn_client
    resp = await local_cdn.get_versions(to_package_name(asset_id))
    await publish_library_version(request, asset_id=asset_id, version=resp['versions'][0], config=config)


@router.post("/publish/{asset_id}/{version}", summary="execute action")
async def publish_library_version(
        request: Request,
        asset_id: str,
        version: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_packages)
    local_package = get_local_package(asset_id=asset_id, config=config)

    async with context.start(action="Sync") as ctx:
        library_name = decode_id(decode_id(asset_id))
        await asyncio.gather(
            send_version_pending(asset_id=asset_id, name=library_name, version=version, context=ctx),
            send_package_pending(package=local_package, context=ctx),
            ctx.info(step=ActionStep.STARTED, content=f"{library_name}#{version}: synchronize")
            )

        base_path = config.pathsBook.local_storage / "cdn" / "youwol-users" / "libraries"
        namespace = None if '/' not in library_name else library_name.split('/')[0][1:]
        library_name = library_name if '/' not in library_name else library_name.split('/')[1]
        library_path = base_path / library_name / version \
            if not namespace \
            else base_path / namespace / library_name / version

        try:
            await post_library(asset_id=asset_id, zip_path=library_path / "__original.zip", context=context)
        finally:
            await ctx.info(
                step=ActionStep.DONE,
                content=f"{library_name}#{version}: synchronization done"
                )
            await check_package_status(package=local_package, context=context, target_versions=[version])


@router.post("/synchronize", summary="sync multiple assets")
async def sync_multiple(
        request: Request,
        body: SyncMultipleBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    queue = asyncio.Queue()
    for asset in body.assetIds:
        queue.put_nowait(asset)

    async def worker(_queue):
        while True:
            target = await _queue.get()
            await publish_library_version(request=request, asset_id=target.assetId, version=target.version,
                                          config=config)
            queue.task_done()

    tasks = []
    for i in range(5):
        task = asyncio.get_event_loop().create_task(worker(queue))
        tasks.append(task)

    await queue.join()

    for task in tasks:
        task.cancel()

    return {}


@router.post("/publish/{asset_id}", summary="execute action")
async def sync_package(
        request: Request,
        asset_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_packages)
    await context.web_socket.send_json({
        "assetId": asset_id,
        "libraryName": decode_id(decode_id(asset_id)),
        "status": str(PackageStatus.PROCESSING)
        })

    local_package = get_local_package(asset_id=asset_id, config=config)
    assets_gateway_client = await config.get_assets_gateway_client(context=context)

    to_sync_releases = [v.version for v in local_package.releases]

    try:
        raw_metadata, _ = await asyncio.gather(
            assets_gateway_client.get_raw_metadata(kind='package', raw_id=decode_id(asset_id)),
            sync_asset_metadata(
                kind='package',
                asset_id=asset_id,
                assets_gateway_client=assets_gateway_client,
                config=config
                )
            )
        remote_versions = {release['version']: release['fingerprint'] for release in raw_metadata['releases']}
        local_versions = {release.version: release.fingerprint for release in local_package.releases}

        missing = [v for v in local_versions.keys() if v not in remote_versions]
        mismatch = [v for v, checksum in local_versions.items()
                    if v in remote_versions and checksum != remote_versions[v]]
        to_sync_releases = missing + mismatch

    except HTTPException as e:
        if e.status_code != 404:
            raise e

    for version in to_sync_releases:
        await publish_library_version(request=request, asset_id=asset_id, version=version, config=config)

    if not to_sync_releases:
        package = get_local_package(asset_id, config)
        await check_package_status(package=package, context=context)

    return {}


@router.get("/status",
            summary="execute action",
            response_model=LibrariesList)
async def status(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.upload_packages)
    await context.config.get_auth_token(context)

    items_treedb = parse_json(config.pathsBook.local_docdb / "tree_db" / "items" / "data.json")
    packages_treedb = [d for d in items_treedb['documents'] if d['type'] == 'package']
    dict_treedb = defaultdict(list)
    packages = await get_all_packages(context)
    packages_name = set(p.info.name for p in packages)

    for item in packages_treedb:

        metadata = json.loads(item['metadata'])
        asset_id = decode_id(metadata['relatedId'])
        if asset_id not in packages_name:
            continue

        raw_id = metadata['relatedId']
        asset_id = decode_id(metadata['relatedId'])
        dict_treedb[asset_id].append(TreeItem(
            name=item['name'],
            itemId=item['item_id'],
            group=to_group_scope(item['group_id']),
            borrowed=metadata['borrowed'],
            rawId=raw_id
            ))

    data_packages = parse_json(config.pathsBook.local_docdb / "cdn" / "libraries" / "data.json")
    data_packages = [p for p in data_packages['documents'] if p['library_name'] in packages_name]
    data = sorted(data_packages, key=lambda d: d['library_name'])
    libraries = []

    raw_ids = []

    for k, g in groupby(data, key=lambda d: d['library_name']):

        releases = list(g)

        raw_id = encode_id(k)
        raw_ids.append(raw_id)

        libraries.append(Library(
            libraryName=k,
            namespace=releases[0]['namespace'],
            treeItems=dict_treedb[k],
            releases=[Release(
                version=r['version'],
                fingerprint=r['fingerprint'] if 'fingerprint' in r else "")
                for r in releases],
            assetId=encode_id(raw_id),
            rawId=raw_id
            ))

    asyncio.run_coroutine_threadsafe(check_all_status(packages=libraries, context=context),
                                     asyncio.get_event_loop())

    return LibrariesList(libraries=libraries)


async def sync_asset_metadata(
        kind: str,
        asset_id: str,
        assets_gateway_client: AssetsGatewayClient,
        config: YouwolConfiguration
        ):

    assets = parse_json(config.pathsBook.local_docdb / "assets" / "entities" / "data.json")
    asset = next((d for d in assets['documents'] if d['asset_id'] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail=f'Local asset {asset_id} not found')
    body = {
        "name": asset['name'],
        "tags": asset["tags"],
        "description": asset["description"]
        }
    remote_meta, _ = await asyncio.gather(
        assets_gateway_client.get_asset_metadata(asset_id),
        assets_gateway_client.update_asset(asset_id, body)
        )
    missing_images = [url for url in asset['images'] if url not in remote_meta['images']]

    def load_image(url: str):
        tail_url = url.split(asset_id+'/')[1]
        img_path = Path(config.pathsBook.local_storage / 'assets' / 'youwol-users' / kind / asset_id / tail_url)
        return [url.split('/')[-1], img_path.read_bytes()]

    images = [load_image(url) for url in missing_images]
    await asyncio.gather(*[assets_gateway_client.post_asset_image(asset_id=asset_id, data={"file": data},
                                                                  filename=filename)
                           for filename, data in images])
    return {}


async def check_all_status(packages: List[Any], context: Context):

    await asyncio.gather(*[check_package_status(package, context=context) for package in packages])


async def check_package_status(
        package: Library,
        context: Context,
        target_versions: List[str] = None
        ):
    target_versions = target_versions or [r.version for r in package.releases]

    async with context.start("Asset status") as ctx:

        await asyncio.gather(
            send_package_pending(package=package, context=ctx),
            *[send_version_pending(asset_id=package.assetId, name=package.libraryName,
                                   version=version, context=ctx)
              for version in target_versions]
            )

        client = await context.config.get_assets_gateway_client(context)
        await ctx.info(step=ActionStep.STATUS, content=f"Check status {package.libraryName}",
                       json=package.dict())

        asset_resp, metadata_resp, tree_resp = await asyncio.gather(
            client.get_asset_metadata(asset_id=package.assetId),
            client.get_raw_metadata(kind="package", raw_id=package.rawId),
            client.get_tree_item(item_id=package.assetId),
            loop=None,
            return_exceptions=True
            )
        asset_status = PackageStatus.NOT_FOUND if isinstance(asset_resp, HTTPException) else PackageStatus.SYNC
        tree_status = PackageStatus.NOT_FOUND if isinstance(tree_resp, HTTPException) else PackageStatus.SYNC

        if isinstance(metadata_resp, HTTPException):
            cdn_status = PackageStatus.NOT_FOUND
            await send_package_resolved(package, asset_status, tree_status, cdn_status, ctx)
            await asyncio.gather(*[
                send_version_resolved(asset_id=package.assetId, name=package.libraryName, version=version,
                                      status=PackageStatus.NOT_FOUND,  context=ctx)
                for version in target_versions])
            return

        remote_versions = {release['version']: release['fingerprint']
                           for release in metadata_resp['releases']}
        local_versions = {release.version: release.fingerprint
                          for release in package.releases}

        for version, fingerprint in local_versions.items():
            if version in remote_versions and remote_versions[version] == fingerprint and version in target_versions:
                await send_version_resolved(asset_id=package.assetId, name=package.libraryName, version=version,
                                            status=PackageStatus.SYNC, context=ctx)
                continue
            if version in remote_versions and remote_versions[version] != fingerprint and version in target_versions:
                await send_version_resolved(asset_id=package.assetId, name=package.libraryName, version=version,
                                            status=PackageStatus.MISMATCH, context=ctx)
                continue
            if version in target_versions:
                await send_version_resolved(asset_id=package.assetId, name=package.libraryName, version=version,
                                            status=PackageStatus.NOT_FOUND, context=ctx)

        if all(version in remote_versions and remote_versions[version] == fingerprint
               for version, fingerprint in local_versions.items()):
            cdn_status = PackageStatus.SYNC

            await send_package_resolved(package, asset_status, tree_status, cdn_status, ctx)
            return

        cdn_status = PackageStatus.MISMATCH

        await send_package_resolved(package, asset_status, tree_status, cdn_status, ctx)


async def post_library(
        asset_id: str,
        zip_path: Path,
        context: Context):

    items_treedb = parse_json(context.config.pathsBook.local_treedb_docdb)
    tree_items = [item for item in items_treedb['documents'] if item['related_id'] == asset_id]
    master_tree_item = [item for item in tree_items if not json.loads(item['metadata'])['borrowed']]
    borrowed_items = [item for item in tree_items if json.loads(item['metadata'])['borrowed']]
    if not master_tree_item:
        raise Exception(f"No reference in the explorer to {asset_id}")

    if len(master_tree_item) > 1:
        raise Exception(f"Multiple non-borrowed reference to the same asset {asset_id}")
    master_tree_item = master_tree_item[0]
    await context.info(
        step=ActionStep.RUNNING,
        content="Found tree items of asset",
        json={
            "masterTreeItem": master_tree_item,
            "borrowedTreeItems": [item for item in borrowed_items]
            }
        )

    tree_id = master_tree_item['item_id']
    path_item = await path(tree_id, context.config)
    client = await context.config.get_assets_gateway_client(context)

    try:
        tree_item = await client.get_tree_item(item_id=tree_id)
        parent_id = tree_item['folderId']

    except HTTPException as e:
        if e.status_code != 404:
            raise e

        await context.info(
            step=ActionStep.RUNNING,
            content="Tree item not found, start creation",
            json={"treeItemPath": to_json(path_item)}
            )
        await ensure_path(path_item, client)
        parent_id = path_item.drive.driveId
        if len(path_item.folders) > 0:
            parent_id = path_item.folders[0].folderId

    data = {'file': zip_path.read_bytes(), 'content_encoding': 'identity'}
    await client.put_asset_with_raw(kind='package', folder_id=parent_id, data=data, group_id=path_item.drive.groupId,
                                    timeout=600)
    await synchronize_permissions_metadata_symlinks(
        asset_id=asset_id,
        tree_id=tree_id,
        assets_gtw_client=client,
        context=context
        )
