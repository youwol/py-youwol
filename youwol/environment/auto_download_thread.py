import asyncio
import uuid
from threading import Thread
from typing import Dict, Any

from youwol.environment.clients import RemoteClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol_utils import YouWolException, encode_id, decode_id


async def process_download_asset(
        queue: asyncio.Queue,
        factories: Dict[str, Any],
        env: YouwolEnvironment
        ):
    while True:
        url, context, headers = await queue.get()
        if "packages_downloaded_ids" not in env.private_cache:
            env.private_cache["packages_downloaded_ids"] = set()
        raw_id = url.split('/api/assets-gateway/raw/')[1].split('/')[1]
        asset_id = encode_id(raw_id)
        remote_gtw_client = await RemoteClients.get_assets_gateway_client(context=context)

        try:
            asset = await remote_gtw_client.get_asset_metadata(asset_id=asset_id, headers=headers)
            raw_id = decode_id(asset_id)
            process_id = str(uuid.uuid4())

            task = factories[asset['kind']](
                process_id=process_id, raw_id=raw_id, asset_id=asset_id, url=url, context=context
            )
            download_id = task.download_id()
            downloaded_ids = env.private_cache["packages_downloaded_ids"]
            up_to_date = await task.is_local_up_to_date()
            if up_to_date:
                await context.info(text="Asset up to date")

            if download_id in downloaded_ids:
                await context.info(text="Asset already in download queue")

            if download_id not in downloaded_ids and not up_to_date:
                downloaded_ids.add(download_id)
                await task.create_local_asset()
        except YouWolException as e:
            print(e)

        queue.task_done()


class AssetDownloadThread(Thread):

    event_loop = asyncio.new_event_loop()
    download_queue = asyncio.Queue(loop=event_loop)
    downloaded_ids = set()

    def __init__(self, factories, worker_count: int):

        def start_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        super().__init__(target=start_loop, args=(self.event_loop,))
        self.worker_count = worker_count
        self.factories = factories

    def go(self, env: YouwolEnvironment):
        super().start()
        tasks = []
        for _ in range(self.worker_count):
            coroutine = process_download_asset(
                queue=self.download_queue,
                env=env,
                factories=self.factories
            )
            task = self.event_loop.create_task(coroutine)
            tasks.append(task)

    def enqueue_asset(self, url: str, context, headers):

        async def enqueue_asset():
            self.download_queue.put_nowait((url, context, headers))

        asyncio.run_coroutine_threadsafe(
            enqueue_asset(),
            self.event_loop
            )

    def join(self, timeout=0):
        async def stop_loop():
            await self.download_queue.join()
            self.event_loop.stop()

        asyncio.run_coroutine_threadsafe(stop_loop(), self.event_loop)
        if self.is_alive():
            super().join(timeout)
