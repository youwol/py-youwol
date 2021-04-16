import asyncio
import base64
import json
import os
import zipfile
from collections import defaultdict
from enum import Enum
from itertools import groupby
from pathlib import Path
from typing import List, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.datastructures import Headers
from starlette.websockets import WebSocket

from youwol_utils import to_group_owner, aiohttp
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from dashboard.back.src.routers.admin.web_socket_cache import WebSocketsCache
from dashboard.back.src.routers.api import apply_authorization_headers
from env.remote_environments import DevEnv
from global_configuration import GlobalConfiguration
from paths import parse_json

router = APIRouter()


class PackageStatus(Enum):
    NOT_FOUND = 'PackageStatus.NOT_FOUND'
    MISMATCH = 'PackageStatus.MISMATCH'
    SYNC = 'PackageStatus.SYNC'
    PROCESSING = 'PackageStatus.PROCESSING'


class SyncMultipleBody(BaseModel):
    assetIds: List[str]


class TreeItem(BaseModel):
    name: str
    itemId: str
    group: str
    borrowed: bool
    rawId: str


class Release(BaseModel):
    version: str
    fingerprint: str


class Library(BaseModel):
    assetId: str
    libraryName: str
    namespace: str
    treeItems: List[TreeItem]
    releases: List[Release]
    rawId: str


class PathResp(BaseModel):
    group: str
    drive: dict
    folders: List[Any]


class LibrariesList(BaseModel):
    libraries: List[Library]


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def encode_id(raw_id) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


def get_local_package(asset_id: str) -> Library:
    """
    Not populated with tree items
    """
    global_config = GlobalConfiguration()
    data_packages = parse_json(global_config.paths_book.docdb_data/"cdn"/"libraries"/"data.json")
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
    WebSocketsCache.assets = ws
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Message text was: {data}")


@router.get("/packages/{tree_id}/path",
            summary="execute action",
            response_model=PathResp)
async def path(tree_id: str) -> PathResp:

    global_config = GlobalConfiguration()
    items_treedb = parse_json(global_config.paths_book.docdb_data/"tree_db"/"items"/"data.json")
    items_treedb = items_treedb['documents']
    folders_treedb = parse_json(global_config.paths_book.docdb_data/"tree_db"/"folders"/"data.json")
    folders_treedb = folders_treedb['documents']
    drives_treedb = parse_json(global_config.paths_book.docdb_data/"tree_db"/"drives"/"data.json")
    drives_treedb = drives_treedb['documents']

    tree_item = next(item for item in items_treedb if item['item_id'] == tree_id)
    tree_drive = next(item for item in drives_treedb if item['drive_id'] == tree_item['drive_id'])

    def path_rec(parent_folder_id) -> List[Any]:
        folder = next((item for item in folders_treedb if item['folder_id'] == parent_folder_id), None)
        if not folder:
            return []
        return [folder] + path_rec(folder['parent_folder_id'])

    return PathResp(
        group=to_group_owner(tree_item['group_id']),
        drive=tree_drive,
        folders=path_rec(tree_item['folder_id'])
        )


@router.post("/packages/{asset_id}/{version}", summary="execute action")
async def publish_library_version(asset_id: str, version: str):

    ws = WebSocketsCache.assets
    library_name = decode_id(decode_id(asset_id))
    await ws.send_json({
        "assetId": asset_id,
        "libraryName": library_name,
        "status": str(PackageStatus.PROCESSING),
        'details': {
            'version': version,
            'info': f'The version {version} is prepared for publishing.'
            }
        })

    global_config = GlobalConfiguration()
    library_name = decode_id(decode_id(asset_id))

    base_path = global_config.paths_book.storage_data / "cdn" / "youwol-users" / "libraries"
    namespace = None if '/' not in library_name else library_name.split('/')[0][1:]
    library_name = library_name if '/' not in library_name else library_name.split('/')[1]
    library_path = base_path / library_name / version \
        if not namespace \
        else base_path / namespace / library_name / version

    files_to_zip = []
    for subdir, dirs, files in os.walk(library_path):
        for filename in files:
            file_path = Path(subdir) / filename
            if filename == f"{version}.zip" or filename == "metadata.json":
                os.remove(file_path)  # in case of left over by a previous publish
            else:
                files_to_zip.append([file_path, file_path.relative_to(library_path)])

    zip_path = library_path / f"{version}.zip"
    try:

        zipper = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        for link in files_to_zip:
            zipper.write(link[0], arcname=link[1])
        zipper.close()
        await post_library(asset_id=asset_id, zip_path=zip_path)
    finally:
        package = get_local_package(asset_id)
        await check_asset_status(package)
        os.remove(zip_path)


@router.post("/packages/{asset_id}", summary="execute action")
async def sync_package(asset_id: str):
    ws = WebSocketsCache.assets
    await ws.send_json({
        "assetId": asset_id,
        "libraryName": decode_id(decode_id(asset_id)),
        "status": str(PackageStatus.PROCESSING)
        })

    local_package = get_local_package(asset_id)
    env = DevEnv(global_configuration=GlobalConfiguration())
    headers = await apply_authorization_headers(Headers(), env)
    headers = {k: v for k, v in headers.items()}
    assets_gateway_client = AssetsGatewayClient(url_base=f"{env.gateway_url}/api/assets-gateway", headers=headers)

    to_sync_releases = [v.version for v in local_package.releases]

    try:
        raw_metadata, _ = await asyncio.gather(
            assets_gateway_client.get_raw_metadata(kind='package', raw_id=decode_id(asset_id)),
            sync_asset_metadata(kind='package', asset_id=asset_id, assets_gateway_client=assets_gateway_client)
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
        await publish_library_version(asset_id, version)

    if not to_sync_releases:
        package = get_local_package(asset_id)
        await check_asset_status(package)

    return {}


@router.post("/packages", summary="sync multiple assets")
async def sync_multiple(body: SyncMultipleBody):

    queue = asyncio.Queue()
    for asset in body.assetIds:
        queue.put_nowait(asset)

    async def worker(_queue):
        while True:
            asset_id = await _queue.get()
            await sync_package(asset_id)
            queue.task_done()

    tasks = []
    for i in range(5):
        task = asyncio.get_event_loop().create_task(worker(queue))
        tasks.append(task)

    await queue.join()

    for task in tasks:
        task.cancel()

    return {}


@router.get("/packages/status",
            summary="execute action",
            response_model=LibrariesList)
async def status():

    global_config = GlobalConfiguration()

    items_treedb = parse_json(global_config.paths_book.docdb_data / "tree_db" / "items" / "data.json")
    packages_treedb = [d for d in items_treedb['documents'] if d['type'] == 'package']
    dict_treedb = defaultdict(list)

    for item in packages_treedb:
        metadata = json.loads(item['metadata'])
        raw_id = metadata['relatedId']
        asset_id = decode_id(metadata['relatedId'])
        dict_treedb[asset_id].append(TreeItem(
            name=item['name'],
            itemId=item['item_id'],
            group=to_group_owner(item['group_id']),
            borrowed=metadata['borrowed'],
            rawId=raw_id
            ))

    data_packages = parse_json(global_config.paths_book.docdb_data / "cdn" / "libraries" / "data.json")
    data = sorted(data_packages['documents'], key=lambda d: d['library_name'])
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

    asyncio.run_coroutine_threadsafe(check_all_status(libraries), asyncio.get_event_loop())

    return LibrariesList(libraries=libraries)


async def sync_asset_metadata(kind: str, asset_id: str, assets_gateway_client: AssetsGatewayClient):

    global_config = GlobalConfiguration()
    assets = parse_json(global_config.paths_book.docdb_data/"assets"/"entities"/"data.json")
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
        img_path = Path(global_config.paths_book.storage_data / 'assets' / 'youwol-users' / kind / asset_id / tail_url)
        return [url.split('/')[-1], img_path.read_bytes()]

    images = [load_image(url) for url in missing_images]
    await asyncio.gather(*[assets_gateway_client.post_asset_image(asset_id=asset_id, data={"file": data},
                                                                  filename=filename)
                           for filename, data in images])
    return {}


async def check_all_status(packages: List[Any]):

    await asyncio.gather(*[check_asset_status(package) for package in packages])


async def check_asset_status(library: Library):

    config = GlobalConfiguration()
    env = DevEnv(global_configuration=config)
    headers = await apply_authorization_headers(Headers(), env)
    url = f"{env.gateway_url}/api/assets-gateway/raw/package/metadata/{library.rawId}"
    ws = WebSocketsCache.assets
    headers = {k: v for k, v in headers.items()}

    async with aiohttp.ClientSession() as session:
        async with await session.get(url=url, headers=headers) as resp:

            status_code = resp.status
            resp = await resp.json()
            if status_code == 404:
                await ws.send_json({
                    "assetId": library.assetId,
                    "libraryName": library.libraryName,
                    'status': str(PackageStatus.NOT_FOUND),
                    'details': {}
                    })
                return
            remote_versions = {release['version']: release['fingerprint'] for release in resp['releases']}
            local_versions = {release.version: release.fingerprint for release in library.releases}

            if remote_versions == local_versions:
                await ws.send_json({
                    "assetId": library.assetId,
                    "libraryName": library.libraryName,
                    'status': str(PackageStatus.SYNC),
                    'details': {}
                    })
                return

            await ws.send_json({
                "assetId": library.assetId,
                "libraryName": library.libraryName,
                "status": str(PackageStatus.MISMATCH),
                'details': {
                    "missing": [v for v, _ in local_versions.items() if v not in remote_versions],
                    "mismatch": [v for v, checksum in local_versions.items()
                                 if v in remote_versions and checksum != remote_versions[v]],
                    "sync": [v for v, checksum in local_versions.items()
                             if v in remote_versions and checksum == remote_versions[v]]
                    }
                })


async def post_library(asset_id: str, zip_path: Path):

    config = GlobalConfiguration()
    env = DevEnv(global_configuration=config)
    items_treedb = parse_json(config.paths_book.docdb_data/"tree_db"/"items"/"data.json")
    tree_item = [item for item in items_treedb['documents']
                 if item['related_id'] == asset_id and not json.loads(item['metadata'])['borrowed']]

    if not tree_item:
        raise Exception(f"No reference in the explorer to {asset_id}")

    if len(tree_item) > 1:
        raise Exception(f"Multiple non-borrowed reference to the same asset {asset_id}")
    tree_item = tree_item[0]
    tree_id = tree_item['item_id']
    path_item = await path(tree_id)

    headers = await apply_authorization_headers(Headers(), env)
    headers = {k: v for k, v in headers.items()}
    assets_gateway_client = AssetsGatewayClient(url_base=f"{env.gateway_url}/api/assets-gateway", headers=headers)
    # 1 retrieve eventual tree item and if here make sure the asset_id is the same
    # item = await get_tree_item(tree_id=tree_id, env=env, headers=headers)

    try:
        await assets_gateway_client.get_tree_item(item_id=tree_id)
        # if tree-item exists we use it
    except HTTPException as e:
        if e.status_code == 404:
            await ensure_path(path_item, assets_gateway_client)
        if e.status_code != 404:
            raise e

    data = {'file': open(zip_path, 'rb'), 'content_encoding': 'brotli'}
    folder = path_item.folders[0]
    await assets_gateway_client.put_asset_with_raw(kind='package', folder_id=folder['folder_id'],
                                                   data=data, group_id=folder['group_id'])


async def ensure_path(path_item: PathResp, assets_gateway_client: AssetsGatewayClient):

    folders = path_item.folders
    try:
        await assets_gateway_client.get_tree_folder(folder_id=folders[0]['folder_id'])
    except HTTPException as e:
        if e.status_code == 404:
            if len(folders) == 1:
                await ensure_drive(path_item.drive, assets_gateway_client)
            else:
                await ensure_path(PathResp(drive=path_item.drive, group=path_item.group, folders=folders[1:]),
                                  assets_gateway_client)
            folder = folders[0]
            body = {"folderId":  folder['folder_id'], "name": folder['name']}
            await assets_gateway_client.create_folder(parent_folder_id=folder["parent_folder_id"], body=body)


async def ensure_drive(drive: Any,  assets_gateway_client: AssetsGatewayClient):

    try:
        await assets_gateway_client.get_tree_drive(drive_id=drive['drive_id'])
    except HTTPException as e:
        if e.status_code == 404:
            body = {"driveId": drive['drive_id'], "name": drive['name']}
            await assets_gateway_client.create_drive(group_id=drive['group_id'], body=body)
            return
        raise e
