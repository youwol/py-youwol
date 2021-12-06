import asyncio
import base64
import json
import pprint
import time
import uuid
from itertools import groupby
from threading import Thread
from typing import List, Set, cast, Callable

from configuration import RemoteClients
from context import Context
from routers.commons import ensure_path
from services.backs.treedb.models import PathResponse, ItemResponse, ItemsResponse
from utils_low_level import JSON
from youwol_utils import YouWolException
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.treedb.treedb import TreeDbClient


class DownloadLogger:

    messages = []

    async def info(self, process_id: str, title: str, **kwargs):
        self.messages.append({**{'title': title, 'time': time.time(), 'process_id': process_id, 'level': 'info'},
                              **kwargs})

    async def error(self, process_id: str, title: str, **kwargs):
        self.messages.append({**{'title': title, 'time': time.time(), 'process_id': process_id, 'level': 'error'},
                              **kwargs})

    def dumps(self):
        print("##### Dump logger")
        messages = sorted(self.messages, key=lambda _: _['time'])
        messages = sorted(messages, key=lambda _: _['process_id'])

        for k, g in groupby(messages, lambda _: _['process_id']):
            print("=> Process", k)
            for m in g:
                pprint.pprint(m)

        print("##### Done dump logger")


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def encode_id(raw_id) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


async def get_remote_paths(
        remote_treedb: TreeDbClient,
        tree_items: ItemsResponse
        ):
    items_path_ = await asyncio.gather(*[
        remote_treedb.get_path(item.itemId)
        for item in tree_items.items
        ])
    items_path = [PathResponse(**p) for p in items_path_]

    def is_borrowed(item: ItemResponse):
        return json.loads(item.metadata)['borrowed']

    owning_location = next((path for path in items_path if not is_borrowed(path.item)), None)
    borrowed_locations = [path for path in items_path if is_borrowed(path.item)]
    return owning_location, borrowed_locations


async def get_local_owning_folder_id(
        owning_location: PathResponse,
        local_gtw_client: AssetsGatewayClient,
        context: Context
        ):
    if owning_location:
        await ensure_path(owning_location, local_gtw_client)

    default_drive = await context.config.get_default_drive()
    return owning_location.folders[-1].folderId\
        if owning_location\
        else default_drive.systemPackagesFolderId


async def sync_borrowed_items(
        asset_id: str,
        borrowed_locations: List[PathResponse],
        local_gtw_client: AssetsGatewayClient
        ):
    await asyncio.gather(*[ensure_path(p, local_gtw_client) for p in borrowed_locations])

    await asyncio.gather(*[
        local_gtw_client.borrow_tree_item(
            asset_id,
            {'itemId': p.item.itemId, 'destinationFolderId': p.folders[-1].folderId}
            )
        for p in borrowed_locations
        ])


async def download_package(
        remote_gtw_client: AssetsGatewayClient,
        asset_id: str,
        url: str,
        downloaded_ids: Set[str],
        notify_update_available: Callable[[str, str], None],
        context: Context,
        logger: DownloadLogger
        ):
    # <!> this point is reach either if:
    # (i) the url responded with a 404 in local => the version need to be fetched in local,
    # (ii) a 'latest' is requested => query for eventual update is required,
    # or (iii) a '-next' is requested => query for eventual update is required
    #
    # From the point when the url responded with a 404, the package may have been fetched by a way or another
    # => still needed to check for availability in local CDN.

    version = url.split('/api/assets-gateway/raw/')[1].split('/')[2]
    raw_id = decode_id(asset_id)
    package_name = decode_id(raw_id)

    if package_name+"/"+version in downloaded_ids:
        return
    downloaded_ids.add(package_name+"/"+version)
    process_id = str(uuid.uuid4())
    await logger.info(process_id=process_id,
                      title=f"Lookup for eventual download of {package_name}#{version}",
                      url=url, raw_id=raw_id, package_name=package_name, version=version)

    local_gtw_client: AssetsGatewayClient = context.config.localClients.assets_gateway_client
    remote_treedb = await RemoteClients.get_treedb_client(context)

    meta_local, meta_remote = await asyncio.gather(
        local_gtw_client.cdn_get_package(library_name=package_name, version=version, metadata=True),
        remote_gtw_client.cdn_get_package(library_name=package_name, version=version, metadata=True),
        return_exceptions=True
        )

    if isinstance(meta_remote, Exception):
        await logger.error(process_id=process_id,
                           title=f"Package {package_name}#{version} can not be found in remote youwol")
        return

    if not isinstance(meta_local, Exception):
        meta_local = cast(JSON, meta_local)
        meta_remote = cast(JSON, meta_remote)
        await logger.info(
            process_id=process_id,
            title=f"Local version of {package_name}#{version} is found",
            remote_version=meta_remote['version'], local_version=meta_local['version'],
            remote_fingerprint=meta_remote['fingerprint'], local_fingerprint=meta_local['fingerprint']
            )

        if meta_local['fingerprint'] == meta_remote['fingerprint']:
            await logger.info(process_id=process_id, title=f"Package {package_name}#{version} is up-to-date")
            return

        if meta_local['version'] != meta_remote['version']:
            # when the version requested is 'latest'
            await logger.info(
                process_id=process_id,
                title=f"Package {package_name}#{version} is missing a new version ${meta_remote['version']} => upgrade"
                )
            notify_update_available(package_name, meta_remote['version'])
            return

        if meta_local['fingerprint'] != meta_remote['fingerprint']:
            # when the version requested is 'latest'
            await logger.info(
                process_id=process_id,
                title=f"Local CDN is missing modifications on {package_name}#{version} => upgrade"
                )
            notify_update_available(package_name, meta_remote['version'])
            return

    await logger.info(
        process_id=process_id,
        title=f"Proceed to package download of {package_name}#{meta_remote['version']}"
        )
    pack, metadata, tree_items = await asyncio.gather(
        remote_gtw_client.cdn_get_package(library_name=package_name, version=version),
        remote_gtw_client.get_asset_metadata(asset_id=asset_id),
        remote_treedb.get_items_from_related_id(related_id=asset_id)
        )

    owning_location, borrowed_locations = await get_remote_paths(
        remote_treedb=remote_treedb,
        tree_items=ItemsResponse(**tree_items)
        )
    owning_folder_id = await get_local_owning_folder_id(
        owning_location=owning_location,
        local_gtw_client=local_gtw_client,
        context=context
        )
    await local_gtw_client.put_asset_with_raw(
        kind='package',
        folder_id=owning_folder_id,
        data={'file': pack}
        )
    await sync_borrowed_items(asset_id=asset_id, borrowed_locations=borrowed_locations,
                              local_gtw_client=local_gtw_client)

    await logger.info(
        process_id=process_id,
        title=f"Package {package_name}#{meta_remote['version']} downloaded successfully"
        )
    print("\n\n")


async def process_download_asset(
        queue: asyncio.Queue,
        downloaded_ids: set[str],
        logger: DownloadLogger,
        notify_update_available: Callable[[str, str], None],
        ):

    while True:
        url, context, headers = await queue.get()

        raw_id = url.split('/api/assets-gateway/raw/')[1].split('/')[1]
        asset_id = encode_id(raw_id)
        remote_gtw_client = await context.config.get_assets_gateway_client(context=context)
        try:
            asset = await remote_gtw_client.get_asset_metadata(asset_id=asset_id, headers=headers)
            if asset['kind'] == 'package':
                await download_package(
                    remote_gtw_client=remote_gtw_client,
                    asset_id=asset_id,
                    url=url,
                    downloaded_ids=downloaded_ids,
                    notify_update_available=notify_update_available,
                    context=context,
                    logger=logger
                    )
        except YouWolException as e:
            print(e)
        queue.task_done()
        print("remaining asset to download in the queue:", queue.qsize())
        if queue.qsize() == 0:
            pprint.pprint(logger.dumps())


async def enqueue_asset(download_queue, raw_id, context, headers):
    download_queue.put_nowait((raw_id, context, headers))


def get_thread_asset_auto_download(notify_update_available: Callable[[str, str], None]):

    downloaded_ids = set()
    download_logger = DownloadLogger()

    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    new_loop = asyncio.new_event_loop()
    t = Thread(target=start_loop, args=(new_loop,))
    t.start()

    download_queue = asyncio.Queue(loop=new_loop)

    tasks = []
    for i in range(4):
        coroutine = process_download_asset(
            queue=download_queue,
            downloaded_ids=downloaded_ids,
            logger=download_logger,
            notify_update_available=notify_update_available
            )
        task = new_loop.create_task(coroutine)
        tasks.append(task)

    asyncio.run_coroutine_threadsafe(download_queue.join(), new_loop)

    return download_queue, new_loop
