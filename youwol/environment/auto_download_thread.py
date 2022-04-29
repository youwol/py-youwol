import asyncio
import uuid
from enum import Enum
from threading import Thread
from typing import Dict, Any

from pydantic import BaseModel

from youwol.environment.clients import RemoteClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.web_socket import UserContextLogger
from youwol_utils import encode_id
from youwol_utils.context import Context


class DownloadEventType(Enum):
    enqueued = "enqueued"
    started = "started"
    succeeded = "succeeded"
    failed = "failed"


class DownloadEvent(BaseModel):
    rawId: str
    kind: str
    type: DownloadEventType


async def process_download_asset(
        queue: asyncio.Queue,
        factories: Dict[str, Any]
        ):

    async def on_error(text, _error, _ctx):
        await _ctx.error(
            text=text,
            data={"rawId": raw_id, "assetId": asset_id, "error": e.__dict__}
        )
        await _ctx.send(DownloadEvent(
            kind=_ctx.with_attributes['kind'],
            rawId=_ctx.with_attributes['rawId'],
            type=DownloadEventType.failed
        ))
    while True:
        url, kind, raw_id, context, headers = await queue.get()
        async with context.start(
                action=f"Proceed download task",
                with_attributes={"kind": kind, "rawId": raw_id},
                on_exit=queue.task_done()
        ) as ctx:  # types: Context

            env = await ctx.get("env", YouwolEnvironment)
            if "packages_downloaded_ids" not in env.private_cache:
                env.private_cache["packages_downloaded_ids"] = set()

            try:
                asset_id = encode_id(raw_id)
                remote_gtw_client = await RemoteClients.get_assets_gateway_client(context=ctx)
                asset = await remote_gtw_client.get_asset_metadata(asset_id=asset_id, headers=headers)
            except Exception as e:
                await on_error("The asset of corresponding rawId is not found in remote", e, ctx)
                return

            process_id = str(uuid.uuid4())

            task = factories[asset['kind']](
                process_id=process_id, raw_id=raw_id, asset_id=asset_id, url=url, context=ctx
            )
            download_id = task.download_id()
            downloaded_ids = env.private_cache["packages_downloaded_ids"]
            up_to_date = await task.is_local_up_to_date()
            if up_to_date:
                await ctx.info(text="Asset up to date")

            if download_id in downloaded_ids:
                await ctx.info(text="Asset already in download queue")

            if download_id not in downloaded_ids and not up_to_date:
                downloaded_ids.add(download_id)
                try:
                    await ctx.send(DownloadEvent(
                        kind=asset['kind'],
                        rawId=raw_id,
                        type=DownloadEventType.started
                    ))
                    await task.create_local_asset()
                    await ctx.send(DownloadEvent(
                        kind=asset['kind'],
                        rawId=raw_id,
                        type=DownloadEventType.succeeded
                    ))
                except Exception as e:
                    await on_error("Error while installing the asset in local",  e, ctx)
                finally:
                    downloaded_ids.remove(download_id)


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

    def go(self):
        super().start()
        tasks = []
        for _ in range(self.worker_count):
            coroutine = process_download_asset(
                queue=self.download_queue,
                factories=self.factories
            )
            task = self.event_loop.create_task(coroutine)
            tasks.append(task)

    def enqueue_asset(self, url: str, kind: str, raw_id: str, context: Context, headers):

        async def enqueue_asset():
            async with context.start(
                    action=f"Enqueue download task of type '{kind}'",
                    with_attributes={
                        'kind': kind,
                        'raw_id': raw_id,
                    },
                    with_loggers=[UserContextLogger()]
            ) as ctx:
                await ctx.send(DownloadEvent(
                    kind=kind,
                    rawId=raw_id,
                    type=DownloadEventType.enqueued
                ))
                self.download_queue.put_nowait((url, kind, raw_id, ctx, headers))

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
