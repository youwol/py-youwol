# standard library
import asyncio
import json
import time

from collections.abc import Callable

# typing
from typing import Any

# third parties
import aiohttp

from starlette.websockets import WebSocket

# relative
from .models import ContextReporter, Label, LogEntry, format_message


class WsContextReporter(ContextReporter):
    """
    Base class for context reporters using web sockets.
    """

    websockets_getter: Callable[[], list[WebSocket]]
    """
    Callback that provides a list of web socket channels to use.
    This function is evaluated each time [log](@yw-nav-meth:WsContextReporter.log) is called.
    """

    mute_exceptions: bool
    """
    If `True` exceptions while sending the message in a web socket are not reported.
    """

    def __init__(
        self,
        websockets_getter: Callable[[], list[WebSocket]],
        mute_exceptions: bool = False,
    ):
        """
        Set the class's attributes.

        Parameters:
            websockets_getter: see
                [websockets_getter](@yw-nav-attr:WsContextReporter.websockets_getter)
            mute_exceptions: see
                [websockets_getter](@yw-nav-attr:WsContextReporter.mute_exceptions)
        """
        self.websockets_getter = websockets_getter
        self.mute_exceptions = mute_exceptions

    async def log(self, entry: LogEntry):
        """
        Send a [LogEntry](@yw-nav-class:LogEntry) in the web-socket channels.

        Parameters:
            entry: log to process.
        """
        message = format_message(entry)
        websockets = self.websockets_getter()

        async def dispatch():
            try:
                text = json.dumps(message)
                await asyncio.gather(
                    *[ws.send_text(text) for ws in websockets if ws],
                    return_exceptions=self.mute_exceptions,
                )
            except (TypeError, OverflowError):
                print(f"Error in JSON serialization ({__file__})")

        await dispatch()


class DeployedContextReporter(ContextReporter):
    """
    This [ContextReporter](@yw-nav-class:ContextReporter) logs into the standard
    output using a format understood by most cloud providers (*e.g.* using spanId, traceId).
    """

    async def log(self, entry: LogEntry):
        """
        Use [print](https://docs.python.org/3/library/functions.html#print) to log a serialized version of
         the provided entry.

        Parameters:
            entry: log entry to print.

        """
        prefix = ""
        if str(Label.STARTED) in entry.labels:
            prefix = "<START>"

        if str(Label.DONE) in entry.labels:
            prefix = "<DONE>"
        base = {
            "message": f"{prefix} {entry.text}",
            "level": entry.level.name,
            "spanId": entry.context_id,
            "labels": [str(label) for label in entry.labels],
            "traceId": entry.trace_uid,
            "logging.googleapis.com/spanId": entry.context_id,
            "logging.googleapis.com/trace": entry.trace_uid,
        }

        try:
            print(json.dumps({**base, "data": entry.data}))
        except TypeError:
            print(
                json.dumps(
                    {
                        **base,
                        "message": f"{base['message']} (FAILED PARSING DATA IN JSON)",
                    }
                )
            )


class ConsoleContextReporter(ContextReporter):
    """
    This [ContextReporter](@yw-nav-class:ContextReporter) logs into the standard
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
    This [ContextReporter](@yw-nav-class:ContextReporter) send logs through
    an API call to a running youwol server in localhost.

    It uses a POST request at `http://localhost:{self.py_youwol_port}/admin/system/logs` with provided headers.

    See [post_logs](@yw-nav-func:post_logs).
    """

    py_youwol_port: int
    """
    Port used on localhost to execute the POST request of the log.
    """
    headers: dict[str, str]
    """
    Headers associated to the POST request of the log.
    """

    def __init__(self, py_youwol_port: int, headers: dict[str, str] | None = None):
        """
        Set the class's attributes.

        Parameters:
            py_youwol_port: see
                [py_youwol_port](@yw-nav-attr:PyYouwolContextReporter.py_youwol_port)
            headers: see
                [headers](@yw-nav-attr:PyYouwolContextReporter.headers)
        """
        super().__init__()
        self.py_youwol_port = py_youwol_port
        self.headers = headers or {}

    async def log(self, entry: LogEntry):
        """
        Send the log to a py-youwol running server using provided
        [port](@yw-nav-attr:PyYouwolContextReporter.py_youwol_port) and
        [headers](@yw-nav-attr:PyYouwolContextReporter.headers).

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
    Stores logs generated from [context](youwol.utils.context.Context) in memory.
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

    They are created from the context using [Context.start](@yw-nav-meth:Context.start) or
    [Context.start_ep](@yw-nav-meth:Context.start_ep).
    """

    leaf_logs: list[LogEntry] = []
    """
    The list of all 'leaf' logs: those associated to a simple log
     (e.g. [Context.info](@yw-nav-meth:Context.info)).
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
