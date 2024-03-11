# standard library
import asyncio
import uuid

from enum import Enum
from threading import Thread

# typing
from typing import Any

# third parties
from pydantic import BaseModel
from tqdm import tqdm

# Youwol application
from youwol.app.environment.youwol_environment import YouwolEnvironment
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import LogEntry, YouWolException, encode_id, log_error
from youwol.utils.context import Context, ContextReporter

# relative
from .models import DownloadTask


class DownloadEventType(Enum):
    ENQUEUED = "enqueued"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UP_TO_DATE = "up_to_date"


class DownloadEvent(BaseModel):
    rawId: str
    kind: str
    type: DownloadEventType


CACHE_DOWNLOADING_KEY = "download-thread#downloading_ids"


def downloading_pbar(env: YouwolEnvironment):
    return f"Downloading [{','.join(env.cache_py_youwol[CACHE_DOWNLOADING_KEY])}]"


async def process_download_asset(
    queue: asyncio.Queue, factories: dict[str, Any], pbar: tqdm
):
    """
    Asynchronously process asset download tasks from a queue.

    This coroutine continuously retrieves download tasks from the provided queue and processes each
    one according to the asset kind specified. It handles the asset download process, including checking
    if the asset is up-to-date, initiating the download, and logging the download status (started, succeeded, failed).

    Parameters:
        queue: The queue from which download tasks are retrieved. Each item in the queue
            is expected to be a tuple containing the URL, kind, raw ID, and context of the asset to download.
        factories: A dictionary mapping asset kinds to their respective factory functions
            or classes, which are used to create download tasks for assets of that kind.
        pbar: A tqdm progress bar instance used to visually track the progress of asset downloads.
    """

    async def on_error(text, data, _ctx: Context):
        log_error("Failed to download asset", data)
        await _ctx.error(text=text, data=data)
        await _ctx.send(
            DownloadEvent(
                kind=_ctx.with_attributes["kind"],
                rawId=_ctx.with_attributes["rawId"],
                type=DownloadEventType.FAILED,
            )
        )

    while True:
        url, kind, raw_id, context = await queue.get()

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
            await context.send(
                DownloadEvent(
                    kind=kind, rawId=raw_id, type=DownloadEventType.UP_TO_DATE
                )
            )
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
                        kind=kind, rawId=raw_id, type=DownloadEventType.STARTED
                    )
                )
                await task.create_local_asset(context=ctx)
                await ctx.send(
                    DownloadEvent(
                        kind=kind, rawId=raw_id, type=DownloadEventType.SUCCEEDED
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
                        "error": (
                            error.detail
                            if isinstance(error, YouWolException)
                            else str(error)
                        ),
                    },
                    ctx,
                )
            finally:
                queue.task_done()
                if download_id in cache_downloaded_ids:
                    cache_downloaded_ids.remove(download_id)
                pbar.set_description(downloading_pbar(env), refresh=True)


class FinalDownloadStatus(BaseModel):
    """
    Final download status of an asset.
    """

    rawId: str
    """
    Raw ID of the asset.
    """
    succeeded: bool
    """
    Whether the download has been successful.
    """

    context_id: str
    """
    Context ID of the function that handled the download.
    """


class AssetDownloadCompletionReporter(ContextReporter):
    """
    A specialized reporter class for tracking the completion status of asset downloads.

    This reporter listens for log entries related to asset download events and filters
    them based on success or failure outcomes. It uses an asynchronous queue to manage
    and process these events, allowing consumers to wait for specific asset download
    completion statuses.
    """

    SUCCEEDED_TAG = DownloadEventType.SUCCEEDED.value
    FAILED_TAG = DownloadEventType.FAILED.value
    UP_TO_DATE_TAG = DownloadEventType.UP_TO_DATE.value
    DONE_TAGS = [SUCCEEDED_TAG, FAILED_TAG, UP_TO_DATE_TAG]

    def __init__(self):
        self.queue = asyncio.Queue()

    async def log(self, entry: LogEntry):
        """
        Add to an async Queue download event entry if they match success or failure criteria.

        Parameter:
            entry: `LogEntry` generated by the various [Context.send](@yw-nav-meth:Context.send) during the
            download processing.
        """
        if (
            DownloadEvent.__name__ in entry.labels
            and entry.data["type"] in self.DONE_TAGS
        ):
            await self.queue.put(entry)

    async def listen(self, raw_id: str) -> FinalDownloadStatus:
        """
        Asynchronously waits for and returns the final download status of an asset identified by `raw_id`.

        Parameters:
            raw_id: `raw_id` of the asset to listen.

        Return:
            The final status of the download when done.
        """
        while True:
            entry: LogEntry = await self.queue.get()
            if entry.data["rawId"] == raw_id:
                return FinalDownloadStatus(
                    rawId=entry.data["rawId"],
                    succeeded=entry.data["type"]
                    in [self.SUCCEEDED_TAG, self.UP_TO_DATE_TAG],
                    context_id=entry.parent_context_id,
                )


class AssetDownloadThread(Thread):
    """
    A thread class designed to manage the asynchronous downloading of assets in a separate event loop.

    This class encapsulates the functionality required to enqueue asset download tasks, monitor their progress,
    and report on their completion status. It utilizes an asyncio event loop running in a separate thread
    to handle concurrent downloads, manage a download queue, and support reporting through a designated reporter
    instance.
    """

    event_loop = asyncio.new_event_loop()
    """
    An asyncio event loop that runs in this thread.
    """
    download_queue = asyncio.Queue()
    """
    A queue for managing download tasks.
    """
    completion_reporter = AssetDownloadCompletionReporter()
    """
    An instance for reporting download events and statuses
    """

    def is_downloading(
        self, url: str, kind: str, raw_id: str, env: YouwolEnvironment
    ) -> bool:
        """
        Checks if an asset is currently being downloaded.

        Parameters:
            url: Original asset request's URL that triggered the download.
            kind: Kind of the asset.
            raw_id: Raw ID of the asset.
            env: Current YouwolEnvironment.

        Return:
            Whether the asset is currently being downloaded.
        """
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

    def enqueue_asset(self, url: str, kind: str, raw_id: str, context: Context):
        """
        Enqueues an asset for downloading.

        Parameters:
            url: Original asset request's URL that triggered the download.
            kind: Kind of the asset.
            raw_id: Raw ID of the asset.
            context: Current context.

        Return:
            Whether the asset is currently being downloaded.
        """

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
                        kind=kind, rawId=raw_id, type=DownloadEventType.ENQUEUED
                    )
                )
                self.download_queue.put_nowait((url, kind, raw_id, ctx))

        asyncio.run_coroutine_threadsafe(enqueue_asset(), self.event_loop)

    async def wait_asset(
        self, url: str, kind: str, raw_id: str, context: Context
    ) -> FinalDownloadStatus:
        """
        Waits for the download of a specific asset and returns its status.

        Parameters:
            url: Original asset request's URL that triggered the download.
            kind: Kind of the asset
            raw_id: Raw ID of the asset
            context: Current context
        Return:
            Download status.
        """
        async with context.start(
            action="Wait asset", with_reporters=[self.completion_reporter]
        ) as ctx:
            self.enqueue_asset(url=url, kind=kind, raw_id=raw_id, context=ctx)
            event = await self.completion_reporter.listen(raw_id=raw_id)
            return event

    def join(self, timeout=0):
        async def stop_loop():
            await self.download_queue.join()
            self.event_loop.stop()

        asyncio.run_coroutine_threadsafe(stop_loop(), self.event_loop)
        if self.is_alive():
            super().join(timeout)
