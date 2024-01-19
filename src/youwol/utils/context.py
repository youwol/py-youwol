# future
from __future__ import annotations

# standard library
import asyncio
import functools
import json
import time
import traceback
import uuid

from abc import ABC, abstractmethod
from collections.abc import Awaitable
from dataclasses import dataclass, field
from enum import Enum
from types import TracebackType

# typing
from typing import Any, Callable, NamedTuple, Type, TypeVar, Union, cast

# third parties
import aiohttp

from fastapi import HTTPException
from pydantic import BaseModel
from starlette.requests import Request
from starlette.websockets import WebSocket

# Youwol utilities
from youwol.utils.types import JSON
from youwol.utils.utils import YouwolHeaders, generate_headers_downstream, to_json

#  Can also be a JSON referencing BaseModel(s), etc
#  At the end 'JsonLike' is anything that can be used in the function 'to_json'
JsonLike = Union[JSON, BaseModel]


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DATA = "DATA"


class Label(Enum):
    STARTED = "STARTED"
    STATUS = "STATUS"
    INFO = "INFO"
    LOG = "LOG"
    APPLICATION = "APPLICATION"
    LOG_INFO = "LOG_INFO"
    LOG_DEBUG = "LOG_DEBUG"
    LOG_ERROR = "LOG_ERROR"
    LOG_WARNING = "LOG_WARNING"
    LOG_ABORT = "LOG_ABORT"
    DATA = "DATA"
    DONE = "DONE"
    EXCEPTION = "EXCEPTION"
    FAILED = "FAILED"
    FUTURE = "FUTURE"
    FUTURE_SUCCEEDED = "FUTURE_SUCCEEDED"
    FUTURE_FAILED = "FUTURE_FAILED"
    MIDDLEWARE = "MIDDLEWARE"
    API_GATEWAY = "API_GATEWAY"
    ADMIN = "ADMIN"
    END_POINT = "END_POINT"
    TREE_DB = "TREE_DB"


T = TypeVar("T")

TContextAttr = int | str | bool


class LogEntry(NamedTuple):
    level: LogLevel
    text: str
    data: JSON
    labels: list[str]
    attributes: dict[str, TContextAttr]
    context_id: str
    parent_context_id: str | None
    trace_uid: str | None
    timestamp: float


DataType = Union[T, Callable[[], T], Callable[[], Awaitable[T]]]


class ContextReporter(ABC):
    @abstractmethod
    async def log(self, entry: LogEntry):
        return NotImplemented


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


class WsContextReporter(ContextReporter):
    def __init__(
        self,
        websockets_getter: Callable[[], list[WebSocket]],
        mute_exceptions: bool = False,
    ):
        self.websockets_getter = websockets_getter
        self.mute_exceptions = mute_exceptions

    async def log(self, entry: LogEntry):
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


StringLike = Any

HeadersFwdSelector = Callable[[list[str]], list[str]]


@dataclass(frozen=True)
class Context:
    logs_reporters: list[ContextReporter] = field(default_factory=list)
    data_reporters: list[ContextReporter] = field(default_factory=list)
    request: Request | None = None

    uid: str = "root"
    parent_uid: str | None = None
    trace_uid: str | None = None

    with_data: dict[str, DataType] = field(default_factory=dict)
    with_attributes: dict[str, TContextAttr] = field(default_factory=dict)
    with_labels: list[str] = field(default_factory=list)
    with_headers: dict[str, str] = field(default_factory=dict)
    with_cookies: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_request(request: Request):
        return cast(Context, request.state.context)

    def start(
        self,
        action: str,
        with_labels: list[StringLike] | None = None,
        with_attributes: dict[str, TContextAttr] | None = None,
        with_data: dict[str, DataType] | None = None,
        with_headers: dict[str, str] | None = None,
        with_cookies: dict[str, str] | None = None,
        on_enter: CallableBlock | None = None,
        on_exit: CallableBlock | None = None,
        on_exception: CallableBlockException | None = None,
        with_reporters: list[ContextReporter] | None = None,
    ) -> ScopedContext:
        with_attributes = with_attributes or {}
        with_labels = with_labels or []
        with_data = with_data or {}
        logs_reporters = (
            self.logs_reporters
            if with_reporters is None
            else self.logs_reporters + with_reporters
        )

        return ScopedContext(
            action=action,
            on_enter=on_enter,
            on_exit=on_exit,
            on_exception=on_exception,
            logs_reporters=logs_reporters,
            data_reporters=self.data_reporters,
            uid=str(uuid.uuid4()),
            request=self.request,
            parent_uid=self.uid,
            trace_uid=self.trace_uid,
            with_labels=[*self.with_labels, *with_labels],
            with_attributes={**self.with_attributes, **with_attributes},
            with_data={**self.with_data, **with_data},
            with_headers={**self.with_headers, **(with_headers or {})},
            with_cookies={**self.with_cookies, **(with_cookies or {})},
        )

    @staticmethod
    def start_ep(
        request: Request,
        action: str | None = None,
        with_labels: list[StringLike] | None = None,
        with_attributes: dict[str, TContextAttr] | None = None,
        body: BaseModel | None = None,
        response: Callable[[], BaseModel] | None = None,
        with_reporters: list[ContextReporter] | None = None,
        on_enter: CallableBlock | None = None,
        on_exit: CallableBlock | None = None,
    ) -> ScopedContext:
        context = Context.from_request(request=request)
        action = action or f"{request.method}: {request.scope['path']}"
        with_labels = with_labels or []
        with_attributes = with_attributes or {}

        async def on_exit_fct(ctx):
            if response:
                await ctx.info("Response", data=response())
            if on_exit:
                await on_exit(ctx)

        async def on_enter_fct(ctx):
            if body:
                await ctx.info("Body", data=body)
            if on_enter:
                await on_enter(ctx)

        return context.start(
            action=action,
            with_labels=[Label.END_POINT, *with_labels],
            with_attributes={"method": request.method, **with_attributes},
            with_reporters=with_reporters,
            on_enter=on_enter_fct,
            on_exit=on_exit_fct,
        )

    async def log(
        self,
        level: LogLevel,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        if not self.data_reporters and not self.logs_reporters:
            return

        json_data = to_json(data) if data else {}
        label_level = {
            LogLevel.DATA: Label.DATA,
            LogLevel.WARNING: Label.LOG_WARNING,
            LogLevel.DEBUG: Label.LOG_DEBUG,
            LogLevel.INFO: Label.LOG_INFO,
            LogLevel.ERROR: Label.LOG_ERROR,
        }[level]
        labels = labels or []
        labels = [str(label) for label in [*self.with_labels, label_level, *labels]]
        entry = LogEntry(
            level=level,
            text=text,
            data=json_data,
            labels=labels,
            attributes=self.with_attributes,
            context_id=self.uid,
            parent_context_id=self.parent_uid,
            trace_uid=self.trace_uid,
            timestamp=time.time() * 1e6,
        )
        if level == LogLevel.DATA:
            await asyncio.gather(*[logger.log(entry) for logger in self.data_reporters])

        await asyncio.gather(*[logger.log(entry) for logger in self.logs_reporters])

    async def send(self, data: BaseModel, labels: list[StringLike] | None = None):
        labels = labels or []
        await self.log(
            level=LogLevel.DATA,
            text=f"Send data '{data.__class__.__name__}'",
            labels=[data.__class__.__name__, *labels],
            data=data,
        )

    async def debug(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        await self.log(level=LogLevel.DEBUG, text=text, labels=labels, data=data)

    async def info(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        await self.log(level=LogLevel.INFO, text=text, labels=labels, data=data)

    async def warning(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        await self.log(level=LogLevel.WARNING, text=text, labels=labels, data=data)

    async def error(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        await self.log(level=LogLevel.ERROR, text=text, labels=labels, data=data)

    async def failed(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        labels = labels or []
        await self.log(
            level=LogLevel.ERROR, text=text, labels=[Label.FAILED, *labels], data=data
        )

    async def future(
        self,
        text: str,
        future: asyncio.Future | None = None,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        labels = labels or []
        await self.log(
            level=LogLevel.INFO, text=text, labels=[Label.FUTURE, *labels], data=data
        )
        if future is None:
            return

        def done_callback(task):
            if task.cancelled():
                asyncio.ensure_future(
                    self.log(
                        level=LogLevel.WARNING,
                        text=f"Future '{text}' cancelled",
                        labels=[*labels],
                        data=data,
                    )
                )
            elif task.exception() is not None:
                asyncio.ensure_future(
                    self.log(
                        level=LogLevel.ERROR,
                        text=f"Future '{text}' resolved with exception",
                        labels=[Label.FUTURE_FAILED, *labels],
                        data=data,
                    )
                )
                raise task.exception()
            else:
                asyncio.ensure_future(
                    self.log(
                        level=LogLevel.INFO,
                        text=f"Future '{text}' resolved successfully",
                        labels=[Label.FUTURE_SUCCEEDED, *labels],
                        data=data,
                    )
                )

        future.add_done_callback(done_callback)

    async def get(self, att_name: str, _object_type: Type[T]) -> T:
        result = self.with_data[att_name]
        if callable(result):
            result = result()

        if isinstance(result, Awaitable):
            result = await result

        return cast(T, result)

    def headers(self, from_req_fwd: HeadersFwdSelector = lambda _keys: []):
        """
        :param from_req_fwd: selector returning the list of header's keys to forward given the header's keys
        of the initiating request of the context.
        :return: headers with all contribution (from YouWol, from original request & from eventual contribution at each
        context's scope)
        """
        headers = (
            generate_headers_downstream(
                incoming_headers=self.request.headers, from_req_fwd=from_req_fwd
            )
            if self.request
            else {}
        )
        return {
            **headers,
            YouwolHeaders.correlation_id: self.uid,
            YouwolHeaders.trace_id: self.trace_uid,
            **{k.lower(): v for k, v in self.with_headers.items()},
        }

    def cookies(self):
        cookies = self.request.cookies if self.request else {}
        return {**cookies, **self.cookies}


CallableBlock = Callable[[Context], Union[Awaitable, None]]
CallableBlockException = Callable[[Exception, Context], Union[Awaitable, None]]


LabelsGetter = Callable[[], set[str]]


@dataclass(frozen=True)
class ScopedContext(Context):
    action: str | None = None
    on_enter: CallableBlock | None = None
    on_exit: CallableBlock | None = None
    on_exception: CallableBlockException | None = None

    @functools.cached_property
    def start_time(self):
        return time.time()

    async def __aenter__(self):
        # When middleware are calling 'next' this seems the only way to pass the context through
        # see https://github.com/tiangolo/fastapi/issues/1529
        if self.request and self.request.state:
            self.request.state.context = self

        await self.info(text=f"{self.action}", labels=[Label.STARTED])
        # next call initialize cache property
        _ = self.start_time
        await ScopedContext.__execute_block(self, self.on_enter)

        return self

    # exit the async context manager
    async def __aexit__(
        self,
        exc_type: type[Exception] | None,
        exc: Exception | None,
        tb: TracebackType | None,
    ):
        if exc:
            await self.error(
                text=f"Exception: {str(exc)}",
                data={
                    "detail": exc.detail
                    if isinstance(exc, HTTPException)
                    else "No detail available",
                    "traceback": traceback.format_exc().split("\n"),
                },
                labels=[Label.EXCEPTION, Label.FAILED],
            )
            await ScopedContext.__execute_block(self, self.on_exception, exc)
            await ScopedContext.__execute_block(self, self.on_exit)
            # False indicates that exception has not been handled
            return False

        await self.info(
            text=f"{self.action} in {int(1000 * (time.time() - self.start_time))} ms",
            labels=[Label.DONE],
        )
        await self.__execute_block(self, self.on_exit)

    @staticmethod
    async def __execute_block(
        ctx: Context,
        block: CallableBlock | CallableBlockException | None,
        exception: Exception | None = None,
    ):
        if not block:
            return
        r = (
            cast(CallableBlockException, block)(exception, ctx)
            if exception
            else cast(CallableBlock, block)(ctx)
        )
        if isinstance(r, Awaitable):
            await r


class ContextFactory:
    with_static_data: dict[str, DataType] = {}
    with_static_labels: dict[str, LabelsGetter] = {}

    @staticmethod
    def add_labels(key: str, labels: set[str] | LabelsGetter):
        ContextFactory.with_static_labels[key] = (
            labels if callable(labels) else lambda: labels
        )

    @staticmethod
    def get_instance(**kwargs) -> Context:
        static_data = ContextFactory.with_static_data or {}
        static_labels = ContextFactory.with_static_labels or {}
        with_data = kwargs if not static_data else {**static_data, **kwargs}
        with_labels = [label for getter in static_labels.values() for label in getter()]

        return Context(with_labels=with_labels, with_data=with_data, **kwargs)


class DeployedContextReporter(ContextReporter):
    async def log(self, entry: LogEntry):
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
    async def log(self, entry: LogEntry):
        base = {
            "message": entry.text,
            "level": entry.level.name,
            "spanId": entry.context_id,
            "labels": [str(label) for label in entry.labels],
            "traceId": entry.trace_uid,
        }
        print(json.dumps(base))


class PyYouwolContextReporter(ContextReporter):
    def __init__(self, py_youwol_port, headers=None):
        super().__init__()
        self.py_youwol_port = py_youwol_port
        self.headers = headers or {}

    async def log(self, entry: LogEntry):
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
    max_count = 10000

    root_node_logs: list[LogEntry] = []
    node_logs: list[LogEntry] = []
    leaf_logs: list[LogEntry] = []

    errors: set[str] = set()
    futures: set[str] = set()
    futures_succeeded: set[str] = set()
    futures_failed: set[str] = set()

    def clear(self):
        self.root_node_logs = []
        self.node_logs = []
        self.leaf_logs = []

    def resize_if_needed(self, items: list[Any]):
        if len(items) > 2 * self.max_count:
            return items[len(items) - self.max_count :]
        return items

    async def log(self, entry: LogEntry):
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
