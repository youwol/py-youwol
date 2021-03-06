from __future__ import annotations

import asyncio
import json
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from enum import Enum
from typing import Union, NamedTuple, Callable, Awaitable, Optional, List, TypeVar, Dict, cast, Any, \
    AsyncContextManager

import aiohttp
from fastapi import HTTPException
from pydantic import BaseModel
from starlette.requests import Request
from starlette.websockets import WebSocket

from youwol_utils import JSON, to_json, YouwolHeaders, generate_headers_downstream


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


T = TypeVar('T')


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
        "labels": [label for label in entry.labels],
        "text": entry.text,
        "data": entry.data,
        "contextId": entry.context_id,
        "parentContextId": entry.parent_context_id
    }


class WsContextReporter(ContextReporter):

    def __init__(self, websockets_getter: Callable[[], List[WebSocket]]):
        self.websockets_getter = websockets_getter

    async def log(self, entry: LogEntry):
        message = format_message(entry)
        websockets = self.websockets_getter()

        async def dispatch():
            try:
                text = json.dumps(message)
                exceptions = await asyncio.gather(*[ws.send_text(text) for ws in websockets if ws],
                                                  return_exceptions=True)
                if any([isinstance(e, Exception) for e in exceptions]):
                    print("Error in ws.send")
            except (TypeError, OverflowError):
                print("Error in JSON serialization")

        await dispatch()


StringLike = Any


class Context(NamedTuple):
    logs_reporters: List[ContextReporter]
    data_reporters: List[ContextReporter]
    request: Optional[Request] = None

    uid: Union[str, None] = 'root'
    parent_uid: Union[str, None] = None
    trace_uid: Union[str, None] = None

    with_data: Dict[str, DataType] = {}
    with_attributes: JSON = {}
    with_labels: List[str] = []

    @staticmethod
    def from_request(request: Request):
        return cast(Context, request.state.context)

    @asynccontextmanager
    async def start(self,
                    action: str,
                    with_labels: List[StringLike] = None,
                    with_attributes: JSON = None,
                    on_enter: 'CallableBlock' = None,
                    on_exit: 'CallableBlock' = None,
                    on_exception: 'CallableBlockException' = None,
                    with_reporters: List[ContextReporter] = None
                    ) -> AsyncContextManager[Context]:
        with_attributes = with_attributes or {}
        with_labels = with_labels or []
        logs_reporters = self.logs_reporters if with_reporters is None else self.logs_reporters + with_reporters
        ctx = Context(logs_reporters=logs_reporters,
                      data_reporters=self.data_reporters,
                      uid=str(uuid.uuid4()),
                      request=self.request,
                      parent_uid=self.uid,
                      trace_uid=self.trace_uid,
                      with_data=self.with_data,
                      with_labels=[*self.with_labels, *with_labels],
                      with_attributes={**self.with_attributes, **with_attributes})

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
                    'detail': e.detail if isinstance(e, HTTPException) else f"No detail available",
                    'traceback': traceback.format_exc().split('\n'),
                },
                labels=[Label.EXCEPTION, Label.FAILED]
            )
            await Context.__execute_block(ctx, on_exception, e)
            await Context.__execute_block(ctx, on_exit)
            traceback.print_exc()
            if self.request.state:
                self.request.state.context = self
            raise e
        else:
            await ctx.info(text=f"{action} in {int(1000 * (time.time() - start))} ms", labels=[Label.DONE])
            if self.request:
                self.request.state.context = self
            await self.__execute_block(ctx, on_exit)

    @staticmethod
    def start_ep(
            request: Request,
            action: str = None,
            with_labels: List[StringLike] = None,
            with_attributes: JSON = None,
            body: BaseModel = None,
            response: Callable[[], BaseModel] = None,
            with_reporters: List[ContextReporter] = None,
            on_enter: 'CallableBlock' = None,
            on_exit: 'CallableBlock' = None,
    ) -> AsyncContextManager[Context]:
        context = Context.from_request(request=request)
        action = action or f"{request.method}: {request.scope['path']}"
        with_labels = with_labels or []
        with_attributes = with_attributes or {}

        async def on_exit_fct(ctx):
            await ctx.info('Response', data=response()) if response else None
            on_exit and await on_exit(ctx)

        async def on_enter_fct(ctx):
            await ctx.info('Body', data=body) if body else None
            on_enter and await on_enter(ctx)

        return context.start(
            action=action,
            with_labels=[Label.END_POINT, *with_labels],
            with_attributes={"method": request.method, **with_attributes},
            with_reporters=with_reporters,
            on_enter=on_enter_fct,
            on_exit=on_exit_fct
        )

    async def log(self, level: LogLevel, text: str, labels: List[StringLike] = None,
                  data: JsonLike = None):

        if not self.data_reporters and not self.logs_reporters:
            return

        json_data = to_json(data)
        label_level = {
            LogLevel.DATA: Label.DATA,
            LogLevel.WARNING: Label.LOG_WARNING,
            LogLevel.DEBUG: Label.LOG_DEBUG,
            LogLevel.INFO: Label.LOG_INFO,
            LogLevel.ERROR: Label.LOG_ERROR
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
            timestamp=time.time() * 1e6
        )
        if level == LogLevel.DATA:
            await asyncio.gather(*[logger.log(entry) for logger in self.data_reporters])

        await asyncio.gather(*[logger.log(entry) for logger in self.logs_reporters])

    async def send(self, data: BaseModel, labels: List[StringLike] = None):
        labels = labels or []
        await self.log(level=LogLevel.DATA, text=f"Send data '{data.__class__.__name__}'",
                       labels=[data.__class__.__name__, *labels], data=data)

    async def debug(self, text: str, labels: List[StringLike] = None, data: JsonLike = None):
        await self.log(level=LogLevel.DEBUG, text=text, labels=labels, data=data)

    async def info(self, text: str, labels: List[StringLike] = None, data: JsonLike = None):
        await self.log(level=LogLevel.INFO, text=text, labels=labels, data=data)

    async def warning(self, text: str, labels: List[StringLike] = None, data: JsonLike = None):
        await self.log(level=LogLevel.WARNING, text=text, labels=labels, data=data)

    async def error(self, text: str, labels: List[StringLike] = None, data: JsonLike = None):
        await self.log(level=LogLevel.ERROR, text=text, labels=labels, data=data)

    async def failed(self, text: str, labels: List[StringLike] = None, data: JsonLike = None):
        labels = labels or []
        await self.log(level=LogLevel.ERROR, text=text, labels=[Label.FAILED, *labels], data=data)

    async def get(self, att_name: str, object_type: T) -> T():
        result = self.with_data[att_name]
        if isinstance(result, Callable):
            result = result()

        if isinstance(result, Awaitable):
            result = await result

        return cast(object_type, result)

    def headers(self):
        headers = generate_headers_downstream(self.request.headers) if self.request else {}
        return {
            **headers,
            YouwolHeaders.correlation_id: self.uid,
            YouwolHeaders.trace_id: self.trace_uid
        }

    @staticmethod
    async def __execute_block(
            ctx: Context,
            block: Optional[Union[CallableBlock, CallableBlockException]],
            exception: Optional[Exception] = None):
        if not block:
            return
        block = block(ctx) if not exception else block(exception, ctx)
        if isinstance(block, Awaitable):
            await block


CallableBlock = Callable[[Context], Union[Awaitable, None]]
CallableBlockException = Callable[[Exception, Context], Union[Awaitable, None]]


class ContextFactory(NamedTuple):
    with_static_data: Optional[Dict[str, DataType]] = None

    @staticmethod
    def get_instance(
            request: Union[Request, None],
            logs_reporter: ContextReporter,
            data_reporter: ContextReporter,
            **kwargs
    ) -> Context:
        static_data = ContextFactory.with_static_data
        with_data = kwargs if not static_data else {**static_data, **kwargs}

        return Context(request=request,
                       logs_reporters=[logs_reporter],
                       data_reporters=[data_reporter],
                       with_data=with_data)


class DeployedContextReporter(ContextReporter):
    errors = set()

    def __init__(self):
        super().__init__()

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
            "logging.googleapis.com/trace": entry.trace_uid
        }

        try:
            print(json.dumps({**base, "data": entry.data}))
        except TypeError:
            print(json.dumps({**base, "message": f"{base['message']} (FAILED PARSING DATA IN JSON)"}))


class ConsoleContextReporter(ContextReporter):

    def __init__(self):
        super().__init__()

    async def log(self, entry: LogEntry):

        base = {
            "message": entry.text,
            "level": entry.level.name,
            "spanId": entry.context_id,
            "labels": [str(label) for label in entry.labels],
            "traceId": entry.trace_uid
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

    def __init__(self):
        super().__init__()

    def clear(self):
        self.root_node_logs = []
        self.node_logs = []
        self.leaf_logs = []

    def resize_if_needed(self, items: List[any]):
        if len(items) > 2 * self.max_count:
            return items[len(items) - self.max_count:]
        return items

    async def log(self, entry: LogEntry):
        if str(Label.LOG) in entry.labels:
            return

        if str(Label.STARTED) in entry.labels and entry.parent_context_id == 'root':
            self.root_node_logs.append(entry)

        if str(Label.STARTED) in entry.labels and entry.parent_context_id != 'root':
            self.node_logs.append(entry)

        if str(Label.STARTED) not in entry.labels:
            self.leaf_logs.append(entry)

        if str(Label.FAILED) in entry.labels:
            self.errors.add(entry.context_id)

        self.root_node_logs = self.resize_if_needed(self.root_node_logs)
        self.leaf_logs = self.resize_if_needed(self.leaf_logs)
