import asyncio
import base64
from threading import Thread

from context import Context
from youwol_utils import YouWolException
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def encode_id(raw_id) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


async def download_package(remote_gtw_client: AssetsGatewayClient, asset_id: str, url: str, context: Context):
    version = url.split('/api/assets-gateway/raw/')[1].split('/')[2]
    raw_id = decode_id(asset_id)
    package_name = decode_id(raw_id)
    local_gtw_client: AssetsGatewayClient = context.config.localClients.assets_gateway_client
    try:
        _ = await local_gtw_client.cdn_get_package(
            library_name=package_name,
            version=version
            )
        print("\n\n======================================> Package already installed", package_name, version)
        return
    except YouWolException as e:
        if e.status_code == 404:
            pass

    pack = await remote_gtw_client.cdn_get_package(
        library_name=package_name,
        version=version
        )
    default_drive = await context.config.get_default_drive()
    await local_gtw_client.put_asset_with_raw(
        kind='package',
        folder_id=default_drive.downloadFolderId,
        data={'file': pack}
        )
    print("\n\n======================================> Downloaded Package", package_name, version)
    print("\n\n")


async def process_download_asset(_: str, queue: asyncio.Queue):

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
                    context=context
                    )
        except YouWolException as e:
            print(e)
        queue.task_done()
        print("remaining asset to download in the queue:", queue.qsize())


async def enqueue_asset(download_queue, raw_id, context, headers):
    download_queue.put_nowait((raw_id, context, headers))


def start_thread_asset_auto_download():

    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    new_loop = asyncio.new_event_loop()
    t = Thread(target=start_loop, args=(new_loop,))
    t.start()

    download_queue = asyncio.Queue(loop=new_loop)

    tasks = []
    # If worker count is more than 1 we may end-up fetching simultaneously the same asset,
    # a guard is required to prevent that before increasing the worker count
    for i in range(1):
        task = new_loop.create_task(process_download_asset(f'worker-{i}', download_queue))
        tasks.append(task)

    asyncio.run_coroutine_threadsafe(download_queue.join(), new_loop)

    return download_queue, new_loop
