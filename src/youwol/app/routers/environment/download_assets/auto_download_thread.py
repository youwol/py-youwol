# standard library
import asyncio
import uuid

from enum import Enum

# typing
from typing import Protocol

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


class DownloadTaskCreator(Protocol):
    """
    Type definition of a 'download task' creator:
    a callable with named arguments `process_id: str, raw_id: str, asset_id: str, url: str` that return a
    (DownloadTask)[@yw-nav-class:DownloadTask].
    """

    def __call__(
        self, process_id: str, raw_id: str, asset_id: str, url: str
    ) -> DownloadTask: ...


DownloadTaskFactory = dict[str, DownloadTaskCreator]
"""
Factory `asset's kind` -> [DownloadTaskCreator](@yw-nav-class:DownloadTaskCreator).
"""


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


def downloading_pbar(env: YouwolEnvironment):
    return f"Downloading [{','.join(env.cache_py_youwol[CACHE_DOWNLOADING_KEY])}]"


async def download_asset(
    raw_id: str,
    kind: str,
    url: str,
    factories: DownloadTaskFactory,
    pbar: tqdm,
    context: Context,
) -> FinalDownloadStatus | None:
    """
    Process asset download tasks, including checking if the asset is up-to-date, initiating the download,
    and logging the download status (started, succeeded, failed).

    Parameters:
        raw_id: Asset's raw ID.
        kind: Asset's kind.
        url: URL that triggered the download.
        factories: A dictionary mapping asset kinds to their respective factory functions
            or classes, which are used to create download tasks for assets of that kind.
        pbar: A tqdm progress bar instance used to visually track the progress of asset downloads.
        context: Current executing context.

    Return:
        Status of the download if it has been processed, `None` otherwise (meaning the asset is `up-to-date` or already
        queued for download).
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
        await context.info(text="Asset already in download queue")
        return None

    up_to_date = await task.is_local_up_to_date(context=context)
    if up_to_date:
        await context.info(text="Asset up to date")
        return None

    pbar.total = pbar.total + 1
    async with context.start(
        action="Proceed download task",
        with_attributes={"kind": kind, "rawId": raw_id},
    ) as ctx:
        cache_downloaded_ids.add(download_id)
        pbar.set_description(downloading_pbar(env), refresh=True)
        try:
            await ctx.send(
                DownloadEvent(kind=kind, rawId=raw_id, type=DownloadEventType.STARTED)
            )
            await task.create_local_asset(context=ctx)
            await ctx.send(
                DownloadEvent(kind=kind, rawId=raw_id, type=DownloadEventType.SUCCEEDED)
            )
            pbar.update(1)
            return FinalDownloadStatus(
                rawId=raw_id, succeeded=True, context_id=ctx.parent_uid
            )

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
            if download_id in cache_downloaded_ids:
                cache_downloaded_ids.remove(download_id)
            pbar.set_description(downloading_pbar(env), refresh=True)


class AssetsDownloader:
    """
    Manages the asynchronous downloading of assets.

    This class encapsulates the functionality required to enqueue asset download tasks, monitor their progress,
    and report on their completion status. It utilizes an `asyncio.Queue` to handle concurrent downloads.
    """

    def __init__(self, factories, worker_count: int):
        """
        Initializes the instance.

        Parameters:
            factories: the factory for download task creation (w/ asset's kind).
            worker_count: the number of workers.
        """
        self.queue = asyncio.Queue()
        self.workers = []
        self.factories: DownloadTaskFactory = factories
        self.pbar = tqdm(total=0, colour="green")
        self.worker_count = worker_count

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

    async def worker(self):
        """
        Asynchronous method representing a worker that continuously retrieves tasks from the queue
        and processes them.

        Each task retrieved from the queue is expected to be a tuple containing the following elements:
            - url: str: The URL from which the asset needs to be downloaded.
            - kind: str: The type or category of the asset being downloaded.
            - raw_id: str: The identifier of the raw asset being downloaded.
            - context: Context: Current executing context.

        The worker function awaits the retrieval of a task from the queue and then initiates the download
        of the asset corresponding to the provided `URL`, `kind`, `raw_id`, and `context`.
        See [download_asset](@yw-nav-func:download_asset).
        """
        while True:
            (url, kind, raw_id, context) = await self.queue.get()

            await download_asset(
                raw_id=raw_id,
                kind=kind,
                url=url,
                context=context,
                factories=self.factories,
                pbar=self.pbar,
            )
            self.queue.task_done()

    async def enqueue_asset(self, url: str, kind: str, raw_id: str, context: Context):
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

        async with context.start(
            action=f"Enqueue download task of type '{kind}'",
            with_attributes={
                "kind": kind,
                "raw_id": raw_id,
            },
            with_reporters=[LogsStreamer()],
        ) as ctx:
            await ctx.send(
                DownloadEvent(kind=kind, rawId=raw_id, type=DownloadEventType.ENQUEUED)
            )
            await self.queue.put((url, kind, raw_id, ctx))

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
        async with context.start(action="Wait asset"):
            return await download_asset(
                raw_id=raw_id,
                kind=kind,
                url=url,
                context=context,
                factories=self.factories,
                pbar=self.pbar,
            )

    async def start_workers(self):
        """
        Start the workers, their number is defined from the `worker_count` argument of `__init__`.
        """
        self.workers.extend(
            asyncio.create_task(self.worker()) for _ in range(self.worker_count)
        )

    async def stop_workers(self):
        """
        Stop the workers.
        """
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
