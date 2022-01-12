import asyncio
import pprint
import time
import uuid
from itertools import groupby
from threading import Thread
from typing import Dict, Any

from youwol.environment.clients import RemoteClients
from youwol_utils import YouWolException, encode_id, decode_id


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
        self.messages = []


async def process_download_asset(
        queue: asyncio.Queue,
        factories: Dict[str, Any],
        downloaded_ids: set[str],
        logger: DownloadLogger
        ):
    while True:
        url, context, headers = await queue.get()

        raw_id = url.split('/api/assets-gateway/raw/')[1].split('/')[1]
        asset_id = encode_id(raw_id)
        remote_gtw_client = await RemoteClients.get_assets_gateway_client(context=context)
        try:
            asset = await remote_gtw_client.get_asset_metadata(asset_id=asset_id, headers=headers)
            raw_id = decode_id(asset_id)
            process_id = str(uuid.uuid4())
            await logger.info(process_id=process_id,
                              title=f"Lookup for eventual download of asset {asset['kind']} of id {raw_id}",
                              url=url, raw_id=raw_id)

            task = factories[asset['kind']](
                process_id=process_id, raw_id=raw_id, asset_id=asset_id, url=url, context=context
                )
            download_id = task.download_id()
            if download_id not in downloaded_ids and not await task.is_local_up_to_date():
                downloaded_ids.add(download_id)
                await task.create_local_asset()

        except YouWolException as e:
            print(e)
        queue.task_done()
        print("remaining asset to download in the queue:", queue.qsize())
        if queue.qsize() == 0:
            logger.dumps()


class AssetDownloadThread(Thread):

    event_loop = asyncio.new_event_loop()
    download_queue = asyncio.Queue(loop=event_loop)
    downloaded_ids = set()
    logger = DownloadLogger()

    def __init__(self, factories, worker_count: int):

        def start_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        super().__init__(target=start_loop, args=(self.event_loop,))
        self.worker_count = worker_count
        self.factories = factories

    def start(self):
        super().start()
        tasks = []
        for i in range(self.worker_count):
            coroutine = process_download_asset(
                queue=self.download_queue,
                downloaded_ids=self.downloaded_ids,
                factories=self.factories,
                logger=self.logger
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
        super().join(timeout)
