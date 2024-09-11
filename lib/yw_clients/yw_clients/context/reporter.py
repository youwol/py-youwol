# standard library
import json
import time

# typing
from typing import Any

# third parties
import aiohttp

from pydantic import BaseModel
from starlette.responses import Response

# Youwol clients
from yw_clients.context.context import Context, TContextAttr
from yw_clients.context.models import ContextReporter, Label, LogEntry


def format_message(entry: LogEntry):
    return {
        "level": entry.level.name,
        "attributes": entry.attributes,
        "labels": entry.labels,
        "text": entry.text,
        "data": entry.data,
        "contextId": entry.context_id,
        "parentContextId": entry.parent_context_id,
    }


class ConsoleContextReporter(ContextReporter):
    """
    This :class:`ContextReporter <yw_clients.context.models.ContextReporter>` logs into the standard
    output.
    """

    async def log(self, entry: LogEntry):
        """
        Use [print](https://docs.python.org/3/library/functions.html#print) to log a serialized version of
         the provided entry by selecting the attributes `message`, `level`, `spanId`, `labels` and `spanId.

        Parameters:
            entry: Log entry to print.
        """
        base = {
            "message": entry.text,
            "level": entry.level.name,
            "spanId": entry.context_id,
            "labels": [str(label) for label in entry.labels],
            "traceId": entry.trace_uid,
        }
        print(json.dumps(base))


class PyYouwolContextReporter(ContextReporter):
    """
    This :class:`ContextReporter <yw_clients.context.models.ContextReporter>` send logs through
    an API call to a running youwol server in localhost.

    It uses a POST request at `http://localhost:{self.py_youwol_port}/admin/system/logs` with provided headers.

    See :func:`post_logs <youwol.app.routers.system.router.post_logs>`.
    """

    def __init__(self, py_youwol_port: int, headers: dict[str, str] | None = None):
        """
        Set the class's attributes.

        Parameters:
            py_youwol_port: see
                :attr:`py_youwol_port <yw_clients.context.reporter.PyYouwolContextReporter.py_youwol_port>`
            headers: see
                :attr:`headers <yw_clients.context.reporter.PyYouwolContextReporter.headers>`
        """
        super().__init__()
        self.py_youwol_port: int = py_youwol_port
        """
        Port used on localhost to execute the POST request of the log.
        """
        self.headers: dict[str, str] = headers or {}
        """
        Headers associated to the POST request of the log.
        """

    async def log(self, entry: LogEntry):
        """
        Send the log to a py-youwol running server using provided
        :attr:`port <yw_clients.context.reporter.PyYouwolContextReporter.py_youwol_port>` and
        :attr:`headers <yw_clients.context.reporter.PyYouwolContextReporter.headers>`.

        Parameters:
            entry: log entry to print.
        """

        url = f"http://localhost:{self.py_youwol_port}/admin/system/logs"
        body = {
            "logs": [
                {
                    "level": entry.level.name,
                    "attributes": entry.attributes,
                    "labels": entry.labels,
                    "text": entry.text,
                    "data": entry.data,
                    "contextId": entry.context_id,
                    "parentContextId": entry.parent_context_id,
                    "timestamp": int(time.time()),
                    "traceUid": entry.trace_uid,
                }
            ]
        }
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body):
                # nothing to do
                pass


class InMemoryReporter(ContextReporter):
    """
    Stores logs generated from [context](yw_clients.context.Context) in memory.
    """

    max_count = 10000
    """
    Maximum count of logs kept in memory.
    """

    root_node_logs: list[LogEntry] = []
    """
    The list of the root logs.
    """

    node_logs: list[LogEntry] = []
    """
    The list of all 'node' logs: those associated to a function execution (and associated to children logs).

    They are created from the context using :meth:`Context.start <yw_clients.context.context.Context.start>` or
    :meth:`Context.start_ep <yw_clients.context.context.Context.start_ep>`.
    """

    leaf_logs: list[LogEntry] = []
    """
    The list of all 'leaf' logs: those associated to a simple log
     (e.g. :meth:`Context.info <yw_clients.context.context.Context.info>`).
    """
    errors: set[str] = set()
    """
    List of `context_id` associated to errors.
    """
    futures: set[str] = set()
    """
    List of `context_id` associated to futures (eventually not resolved yet).
    """
    futures_succeeded: set[str] = set()
    """
    List of `context_id` associated to succeeded futures.
    """
    futures_failed: set[str] = set()
    """
    List of `context_id` associated to failed futures.
    """

    def clear(self):
        self.root_node_logs = []
        self.node_logs = []
        self.leaf_logs = []

    def resize_if_needed(self, items: list[Any]):
        if len(items) > 2 * self.max_count:
            return items[len(items) - self.max_count :]
        return items

    async def log(self, entry: LogEntry):
        """
        Save the entry in memory.

        Parameters:
            entry: log entry.
        """
        if str(Label.LOG) in entry.labels:
            return

        if str(Label.STARTED) in entry.labels and entry.parent_context_id == "root":
            self.root_node_logs.append(entry)

        if str(Label.STARTED) in entry.labels and entry.parent_context_id != "root":
            self.node_logs.append(entry)

        if str(Label.STARTED) not in entry.labels:
            self.leaf_logs.append(entry)

        if str(Label.FAILED) in entry.labels:
            self.errors.add(entry.context_id)

        if str(Label.FUTURE) in entry.labels:
            self.futures.add(entry.context_id)

        if str(Label.FUTURE_SUCCEEDED) in entry.labels:
            self.futures_succeeded.add(entry.context_id)

        if str(Label.FUTURE_FAILED) in entry.labels:
            self.futures_failed.add(entry.context_id)

        self.root_node_logs = self.resize_if_needed(self.root_node_logs)
        self.leaf_logs = self.resize_if_needed(self.leaf_logs)


class FuturesResponseEnd(BaseModel):
    """
    Model to indicate the streaming's end of a [FuturesResponse](FuturesResponse).
    """


class FuturesResponse(Response):
    """
    This HTTP response is used when asynchronous computations (resolving after the HTTP response is returned)
    are needed.

    Example:
        ```python
        @app.get("/async-job")
        async def async_job(
            request: Request,
            task_id: int = Query(alias="task-id", default=int(time.time() * 1e6)),
        ):
            async def tick_every_second(streamer: FuturesResponse, context: BackendContext):
                async with context.start(action="tick_every_second") as ctx_ticks:
                    for i in range(1, 11):
                        await streamer.next(Data(content=f"Second {i}"), context=ctx_ticks)
                        await asyncio.sleep(1)
                    await streamer.close(context=ctx_ticks)

            async with init_context(request).start(action="/async-job") as ctx:
                response = FuturesResponse(channel_id=str(task_id))
                await ctx.info("Use web socket to send async. messages")
                asyncio.ensure_future(tick_every_second(response, ctx))
                return response
        ```
    """

    media_type = "application/json"
    channelIdKey = "async-channel-id"

    def __init__(
        self,
        channel_id: str,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
    ) -> None:
        super().__init__(
            content={"channelId": channel_id},
            status_code=202,
            headers=headers,
            media_type=media_type,
        )
        self.channel_id = channel_id

    async def next(
        self,
        content: BaseModel,
        context: Context,
        labels: list[str] | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        await context.send(
            data=content,
            labels=[*context.with_labels, *(labels or []), self.channel_id],
            attributes={**(attributes or {}), self.channelIdKey: self.channel_id},
        )

    async def close(self, context: Context):

        await context.send(
            data=FuturesResponseEnd(),
            labels=[self.channel_id],
        )

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
