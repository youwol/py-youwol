# standard library
import asyncio
import sys
import uuid

from enum import Enum
from threading import Thread

# typing
from typing import Any, Dict

# third parties
from pydantic import BaseModel
from tqdm import tqdm

# Youwol application
from youwol.app.environment.youwol_environment import YouwolEnvironment
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import YouWolException, encode_id, log_error
from youwol.utils.context import Context

# relative
from .models import DownloadTask


class DownloadEventType(Enum):
    enqueued = "enqueued"
    started = "started"
    succeeded = "succeeded"
    failed = "failed"


class DownloadEvent(BaseModel):
    rawId: str
    kind: str
    type: DownloadEventType


CACHE_DOWNLOADING_KEY = "download-thread#downloading_ids"


def downloading_pbar(env: YouwolEnvironment):
    return f"Downloading [{','.join(env.cache_py_youwol[CACHE_DOWNLOADING_KEY])}]"


async def process_download_asset(
    queue: asyncio.Queue, factories: Dict[str, Any], pbar: tqdm
):
    async def on_error(text, data, _ctx: Context):
        log_error("Failed to download asset", data)
        await _ctx.error(text=text, data=data)
        await _ctx.send(
            DownloadEvent(
                kind=_ctx.with_attributes["kind"],
                rawId=_ctx.with_attributes["rawId"],
                type=DownloadEventType.failed,
            )
        )

    while True:
        url, kind, raw_id, context, _ = await queue.get()

        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        asset_id = encode_id(raw_id)
        process_id = str(uuid.uuid4())
        task: DownloadTask = factories[kind](
            process_id=process_id, raw_id=raw_id, asset_id=asset_id, url=url
        )
        if CACHE_DOWNLOADING_KEY not in env.cache_py_youwol:
            env.cache_py_youwol[CACHE_DOWNLOADING_KEY] = set()
        cache_downloaded_ids = env.cache_py_youwol[CACHE_DOWNLOADING_KEY]

        download_id = task.download_id()
        if download_id in cache_downloaded_ids:
            queue.task_done()
            await context.info(text="Asset already in download queue")
            continue

        up_to_date = await task.is_local_up_to_date(context=context)
        if up_to_date:
            queue.task_done()
            await context.info(text="Asset up to date")
            continue

        pbar.total = pbar.total + 1
        async with context.start(
            action="Proceed download task",
            with_attributes={"kind": kind, "rawId": raw_id},
        ) as ctx:  # types: Context
            cache_downloaded_ids.add(download_id)
            # log_info(f"Start asset install of kind {kind}: {download_id}")
            pbar.set_description(downloading_pbar(env), refresh=True)
            try:
                await ctx.send(
                    DownloadEvent(
                        kind=kind, rawId=raw_id, type=DownloadEventType.started
                    )
                )
                await task.create_local_asset(context=ctx)
                await ctx.send(
                    DownloadEvent(
                        kind=kind, rawId=raw_id, type=DownloadEventType.succeeded
                    )
                )
                pbar.update(1)
                # log_info(f"Done asset install of kind {kind}: {download_id}")

            except Exception as error:
                await on_error(
                    "Error while installing the asset in local",
                    {
                        "raw_id": raw_id,
                        "asset_id": asset_id,
                        "url": url,
                        "kind": kind,
                        "error": error.detail
                        if isinstance(error, YouWolException)
                        else str(error),
                    },
                    ctx,
                )
            finally:
                queue.task_done()
                if download_id in cache_downloaded_ids:
                    cache_downloaded_ids.remove(download_id)
                pbar.set_description(downloading_pbar(env), refresh=True)


class AssetDownloadThread(Thread):
    event_loop = asyncio.new_event_loop()
    download_queue = (
        # TODO: Remove once python 3.9 support is dropped
        asyncio.Queue(loop=event_loop)  # pylint: disable=unexpected-keyword-arg
        if sys.version_info.minor < 10
        else asyncio.Queue()
    )

    def is_downloading(self, url: str, kind: str, raw_id: str, env: YouwolEnvironment):
        if CACHE_DOWNLOADING_KEY not in env.cache_py_youwol:
            return False
        asset_id = encode_id(raw_id)
        task = self.factories[kind](
            process_id="", raw_id=raw_id, asset_id=asset_id, url=url
        )
        return task.download_id() in env.cache_py_youwol[CACHE_DOWNLOADING_KEY]

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
        pbar = tqdm(total=0, colour="green")
        for _ in range(self.worker_count):
            coroutine = process_download_asset(
                queue=self.download_queue, factories=self.factories, pbar=pbar
            )
            task = self.event_loop.create_task(coroutine)
            tasks.append(task)

    def enqueue_asset(
        self, url: str, kind: str, raw_id: str, context: Context, headers
    ):
        async def enqueue_asset():
            async with context.start(
                action=f"Enqueue download task of type '{kind}'",
                with_attributes={
                    "kind": kind,
                    "raw_id": raw_id,
                },
                with_reporters=[LogsStreamer()],
            ) as ctx:
                await ctx.send(
                    DownloadEvent(
                        kind=kind, rawId=raw_id, type=DownloadEventType.enqueued
                    )
                )
                self.download_queue.put_nowait((url, kind, raw_id, ctx, headers))

        asyncio.run_coroutine_threadsafe(enqueue_asset(), self.event_loop)

    def join(self, timeout=0):
        async def stop_loop():
            await self.download_queue.join()
            self.event_loop.stop()

        asyncio.run_coroutine_threadsafe(stop_loop(), self.event_loop)
        if self.is_alive():
            super().join(timeout)
