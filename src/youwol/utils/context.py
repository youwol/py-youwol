from __future__ import annotations

# standard library
import asyncio
import json
import time
import traceback
import uuid

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from enum import Enum

# typing
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    TypeVar,
    Union,
    cast,
)

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
    MIDDLEWARE = "MIDDLEWARE"
    API_GATEWAY = "API_GATEWAY"
    ADMIN = "ADMIN"
    END_POINT = "END_POINT"
    TREE_DB = "TREE_DB"


T = TypeVar("T")


class LogEntry(NamedTuple):
    level: LogLevel
    text: str
    data: JSON
    labels: List[str]
    attributes: Dict[str, str]
    context_id: str
    parent_context_id: str
    trace_uid: Union[str, None]
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
        websockets_getter: Callable[[], List[WebSocket]],
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

HeadersFwdSelector = Callable[[List[str]], List[str]]


class Context(NamedTuple):
    logs_reporters: List[ContextReporter]
    data_reporters: List[ContextReporter]
    request: Optional[Request] = None

    uid: Union[str, None] = "root"
    parent_uid: Union[str, None] = None
    trace_uid: Union[str, None] = None
    muted_http_errors: Set[int] = set()

    with_data: Dict[str, DataType] = {}
    with_attributes: JSON = {}
    with_labels: List[str] = []
    with_headers: Dict[str, str] = {}
    with_cookies: Dict[str, str] = {}

    @staticmethod
    def from_request(request: Request):
        return cast(Context, request.state.context)

    @asynccontextmanager
    async def start(
        self,
        action: str,
        muted_http_errors: Set[int] = None,
        with_labels: List[StringLike] = None,
        with_attributes: JSON = None,
        with_data: Dict[str, DataType] = None,
        with_headers: Dict[str, str] = None,
        with_cookies: Dict[str, str] = None,
        on_enter: "CallableBlock" = None,
        on_exit: "CallableBlock" = None,
        on_exception: "CallableBlockException" = None,
        with_reporters: List[ContextReporter] = None,
    ) -> AsyncContextManager[Context]:
        with_attributes = with_attributes or {}
        with_labels = with_labels or []
        with_data = with_data or {}
        logs_reporters = (
            self.logs_reporters
            if with_reporters is None
            else self.logs_reporters + with_reporters
        )
        muted_http_errors = self.muted_http_errors.union(muted_http_errors or set())
        if self.request:
            YouwolHeaders.patch_request_mute_http_headers(
                request=self.request, status_muted=muted_http_errors
            )
        ctx = Context(
            logs_reporters=logs_reporters,
            data_reporters=self.data_reporters,
            uid=str(uuid.uuid4()),
            request=self.request,
            parent_uid=self.uid,
            trace_uid=self.trace_uid,
            muted_http_errors=self.muted_http_errors.union(muted_http_errors or set()),
            with_labels=[*self.with_labels, *with_labels],
            with_attributes={**self.with_attributes, **with_attributes},
            with_data={**self.with_data, **with_data},
            with_headers={**self.with_headers, **(with_headers or {})},
            with_cookies={**self.with_cookies, **(with_cookies or {})},
        )

        try:
            # When middleware are calling 'next' this seems the only way to pass information
            # see https://github.com/tiangolo/fastapi/issues/1529
            if self.request:
                self.request.state.context = ctx
            await ctx.info(text=f"{action}", labels=[Label.STARTED])
            start = time.time()
            await Context.__execute_block(ctx, on_enter)
            yield ctx  # NOSONAR => can not find proper type annotation
        except Exception as e:
            await ctx.error(
                text=f"Exception: {str(e)}",
                data={
                    "detail": e.detail
                    if isinstance(e, HTTPException)
                    else "No detail available",
                    "traceback": traceback.format_exc().split("\n"),
                },
                labels=[Label.EXCEPTION, Label.FAILED],
            )
            await Context.__execute_block(ctx, on_exception, e)
            await Context.__execute_block(ctx, on_exit)
            muted = False
            if isinstance(e, HTTPException):
                muted = e.status_code in self.muted_http_errors
            if not muted:
                traceback.print_exc()
            if self.request.state:
                self.request.state.context = self
            raise e
        await ctx.info(
            text=f"{action} in {int(1000 * (time.time() - start))} ms",
            labels=[Label.DONE],
        )
        if self.request:
            self.request.state.context = self
        await self.__execute_block(ctx, on_exit)

    @staticmethod
    def start_ep(
        request: Request,
        action: str = None,
        muted_http_errors: Set[int] = None,
        with_labels: List[StringLike] = None,
        with_attributes: JSON = None,
        body: BaseModel = None,
        response: Callable[[], BaseModel] = None,
        with_reporters: List[ContextReporter] = None,
        on_enter: "CallableBlock" = None,
        on_exit: "CallableBlock" = None,
    ) -> AsyncContextManager[Context]:
        context = Context.from_request(request=request)
        action = action or f"{request.method}: {request.scope['path']}"
        with_labels = with_labels or []
        with_attributes = with_attributes or {}

        muted_http_errors = YouwolHeaders.get_muted_http_errors(request=request).union(
            muted_http_errors or set()
        )

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

        # Hot-fix hiding a bigger problem regarding authorization using context; see #1481
        with_headers = (
            {"original_access_token": context.with_headers["authorization"]}
            if "authorization" in context.with_headers
            else {}
        )
        return context.start(
            action=action,
            muted_http_errors=muted_http_errors,
            with_headers=with_headers,
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
        labels: List[StringLike] = None,
        data: JsonLike = None,
    ):
        if not self.data_reporters and not self.logs_reporters:
            return

        json_data = to_json(data)
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

    async def send(self, data: BaseModel, labels: List[StringLike] = None):
        labels = labels or []
        await self.log(
            level=LogLevel.DATA,
            text=f"Send data '{data.__class__.__name__}'",
            labels=[data.__class__.__name__, *labels],
            data=data,
        )

    async def debug(
        self, text: str, labels: List[StringLike] = None, data: JsonLike = None
    ):
        await self.log(level=LogLevel.DEBUG, text=text, labels=labels, data=data)

    async def info(
        self, text: str, labels: List[StringLike] = None, data: JsonLike = None
    ):
        await self.log(level=LogLevel.INFO, text=text, labels=labels, data=data)

    async def warning(
        self, text: str, labels: List[StringLike] = None, data: JsonLike = None
    ):
        await self.log(level=LogLevel.WARNING, text=text, labels=labels, data=data)

    async def error(
        self, text: str, labels: List[StringLike] = None, data: JsonLike = None
    ):
        await self.log(level=LogLevel.ERROR, text=text, labels=labels, data=data)

    async def failed(
        self, text: str, labels: List[StringLike] = None, data: JsonLike = None
    ):
        labels = labels or []
        await self.log(
            level=LogLevel.ERROR, text=text, labels=[Label.FAILED, *labels], data=data
        )

    async def get(self, att_name: str, object_type: T) -> T():
        result = self.with_data[att_name]
        if isinstance(result, Callable):
            result = result()

        if isinstance(result, Awaitable):
            result = await result

        return cast(object_type, result)

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
            YouwolHeaders.muted_http_errors: ",".join(
                str(s) for s in self.muted_http_errors
            ),
            **{k.lower(): v for k, v in self.with_headers.items()},
        }

    def local_headers(self, from_req_fwd: HeadersFwdSelector = lambda _keys: []):
        headers = self.headers(from_req_fwd)
        if "original_access_token" in headers:
            # Hot-fix hiding a bigger problem regarding authorization using context; see #1481
            headers["authorization"] = self.with_headers["original_access_token"]
        return headers

    def cookies(self):
        cookies = self.request.cookies if self.request else {}
        return {**cookies, **self.cookies}

    @staticmethod
    async def __execute_block(
        ctx: Context,
        block: Optional[Union[CallableBlock, CallableBlockException]],
        exception: Optional[Exception] = None,
    ):
        if not block:
            return
        block = block(ctx) if not exception else block(exception, ctx)
        if isinstance(block, Awaitable):
            await block


CallableBlock = Callable[[Context], Union[Awaitable, None]]
CallableBlockException = Callable[[Exception, Context], Union[Awaitable, None]]


LabelsGetter = Callable[[], Set[str]]


class ContextFactory:
    with_static_data: Dict[str, DataType] = {}
    with_static_labels: Dict[str, LabelsGetter] = {}

    @staticmethod
    def add_labels(key: str, labels: Union[Set[str], LabelsGetter]):
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
    errors = set()

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

    root_node_logs: List[LogEntry] = []
    node_logs: List[LogEntry] = []
    leaf_logs: List[LogEntry] = []

    errors = set()

    def clear(self):
        self.root_node_logs = []
        self.node_logs = []
        self.leaf_logs = []

    def resize_if_needed(self, items: List[any]):
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

        self.root_node_logs = self.resize_if_needed(self.root_node_logs)
        self.leaf_logs = self.resize_if_needed(self.leaf_logs)
