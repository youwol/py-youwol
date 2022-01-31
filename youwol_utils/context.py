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

from pydantic import BaseModel
from starlette.requests import Request
from starlette.websockets import WebSocket

from youwol_utils import JSON, to_json, YouwolHeaders, generate_headers_downstream


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
    data: Any
    labels: List[str]
    attributes: Dict[str, str]
    context_id: str
    parent_context_id: str


DataType = Union[T, Callable[[], T], Callable[[], Awaitable[T]]]


class ContextLogger(ABC):

    @abstractmethod
    async def log(self, entry: LogEntry):
        return NotImplemented


class WsContextLogger(ContextLogger):

    def __init__(self, websockets_getter: Callable[[], List[WebSocket]]):
        self.websockets_getter = websockets_getter

    async def log(self, entry: LogEntry):
        message = {
            "level": entry.level.name,
            "attributes": entry.attributes,
            "labels": [label for label in entry.labels],
            "text": entry.text,
            "data": to_json(entry.data) if isinstance(entry.data, BaseModel) else entry.data,
            "contextId": entry.context_id,
            "parentContextId": entry.parent_context_id
        }
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
    loggers: List[ContextLogger]
    request: Request = None

    uid: Union[str, None] = 'root'
    parent_uid: Union[str, None] = None

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
                    with_loggers: List[ContextLogger] = None
                    ) -> AsyncContextManager[Context]:
        with_attributes = with_attributes or {}
        with_labels = with_labels or []
        ctx = Context(loggers=self.loggers if with_loggers is None else self.loggers + with_loggers,
                      uid=str(uuid.uuid4()),
                      request=self.request,
                      parent_uid=self.uid,
                      with_data=self.with_data,
                      with_labels=[*self.with_labels, *with_labels],
                      with_attributes={**self.with_attributes, **with_attributes})

        async def execute_block(block: Optional[Union[CallableBlock, CallableBlockException]],
                                exception: Optional[Exception] = None):
            if not block:
                return
            block = block(ctx) if not exception else block(exception, ctx)
            if isinstance(block, Awaitable):
                await block

        try:
            # When middleware are calling 'next' this seems the only way to pass information
            # see https://github.com/tiangolo/fastapi/issues/1529
            self.request.state.context = ctx
            await ctx.info(text=action, labels=[Label.STARTED])
            start = time.time()
            await execute_block(on_enter)
            yield ctx
        except Exception as e:
            tb = traceback.format_exc()

            await ctx.error(
                text=f"Exception raised",
                data={
                    'error': str(e),
                    'traceback': tb.split('\n'),
                    'args': [str(arg) for arg in e.args]
                },
                labels=[Label.EXCEPTION, Label.FAILED]
            )
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
            self.request.state.context = self
            raise e
        else:
            await ctx.info(text=f"Done in {int(1000 * (time.time() - start))} ms", labels=[Label.DONE])
            self.request.state.context = self
            await execute_block(on_exit)

    @staticmethod
    def start_ep(
            request: Request,
            action: str = None,
            with_labels: List[StringLike] = None,
            with_attributes: JSON = None,
            body: BaseModel = None,
            response: Callable[[], BaseModel] = None,
            with_loggers: List[ContextLogger] = None,
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
            with_loggers=with_loggers,
            on_enter=on_enter_fct,
            on_exit=on_exit_fct
        )

    async def log(self, level: LogLevel, text: str, labels: List[StringLike] = None,
                  data: Union[JSON, BaseModel] = None):
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
            data=data,
            labels=labels,
            attributes=self.with_attributes,
            context_id=self.uid,
            parent_context_id=self.parent_uid
        )
        await asyncio.gather(*[logger.log(entry) for logger in self.loggers])

    async def send(self, data: BaseModel, labels: List[StringLike] = None):
        labels = labels or []
        await self.log(level=LogLevel.DATA, text=f"Send data '{data.__class__.__name__}'",
                       labels=[data.__class__.__name__, *labels], data=data)

    async def debug(self, text: str, labels: List[StringLike] = None, data: Union[JSON, BaseModel] = None):
        await self.log(level=LogLevel.DEBUG, text=text, labels=labels, data=data)

    async def info(self, text: str, labels: List[StringLike] = None, data: Union[JSON, BaseModel] = None):
        await self.log(level=LogLevel.INFO, text=text, labels=labels, data=data)

    async def warning(self, text: str, labels: List[StringLike] = None, data: Union[JSON, BaseModel] = None):
        await self.log(level=LogLevel.WARNING, text=text, labels=labels, data=data)

    async def error(self, text: str, labels: List[StringLike] = None, data: Union[JSON, BaseModel] = None):
        await self.log(level=LogLevel.ERROR, text=text, labels=labels, data=data)

    async def failed(self, text: str, labels: List[StringLike] = None, data: Union[JSON, BaseModel] = None):
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
        return {**headers, YouwolHeaders.correlation_id: self.uid}


CallableBlock = Callable[[Context], Union[Awaitable, None]]
CallableBlockException = Callable[[Exception, Context], Union[Awaitable, None]]


class ContextFactory(NamedTuple):
    with_static_data: Dict[str, DataType] = None

    @staticmethod
    def get_instance(request: Union[Request, None], logger: ContextLogger, **kwargs) -> Context:
        with_data = kwargs if not ContextFactory.with_static_data else {**ContextFactory.with_static_data, **kwargs}

        return Context(request=request,
                       loggers=[logger],
                       with_data={**ContextFactory.with_static_data, **kwargs})
