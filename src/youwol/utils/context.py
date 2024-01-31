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
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Type,
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
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol.utils.clients.cdn_sessions_storage import CdnSessionsStorageClient
from youwol.utils.clients.request_executor import AioHttpExecutor
from youwol.utils.types import JSON, AnyDict
from youwol.utils.utils import YouwolHeaders, generate_headers_downstream, to_json

JsonLike = Union[JSON, BaseModel]
"""
Represents data structures that can be serialized into a json representation
(can also be `JSON` referencing `BaseModel`).
"""


class LogLevel(str, Enum):
    """
    Available severities when loging.
    """

    DEBUG = "DEBUG"
    """
    See [debug](@yw-nav-meth:youwol.utils.context.Context.debug).
    """

    INFO = "INFO"
    """
    See [info](@yw-nav-meth:youwol.utils.context.Context.info).
    """

    WARNING = "WARNING"
    """
    See [warning](@yw-nav-meth:youwol.utils.context.Context.warning).
    """

    ERROR = "ERROR"
    """
    See [error](@yw-nav-meth:youwol.utils.context.Context.error).
    """

    DATA = "DATA"
    """
    See [send](@yw-nav-meth:youwol.utils.context.Context.send).
    """


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
"""
Allowed [context](@yw-nav-class:youwol.utils.context.Context)'s attribute types.
"""


class LogEntry(NamedTuple):
    """
    LogEntry represents a log, they are created from the class
    [Context](@yw-nav-class:youwol.utils.context.ContextReporter) when
    [starting function](@yw-nav-meth:youwol.utils.context.Context.start) or
    [end-point](@yw-nav-meth:youwol.utils.context.Context.start_ep) as well as
    when logging information (e.g. [info](@yw-nav-meth:youwol.utils.context.Context.info)).

    Log entries are processed by [ContextReporter](@yw-nav-class:youwol.utils.context.ContextReporter) that
    implements the action to trigger when a log entry is created.
    """

    level: LogLevel
    """
    Level (e.g. debug, info, error, *etc.*).
    """

    text: str
    """
    Text.
    """

    data: JSON
    """
    Data associated to the log (set up with the `data` argument of *e.g.*
    [info](@yw-nav-meth:youwol.utils.context.Context.info)).
    """
    labels: list[str]
    """
    Labels associated to the log (set up with the `labels` argument of *e.g.*
    [info](@yw-nav-meth:youwol.utils.context.Context.info)).
    """
    attributes: dict[str, TContextAttr]
    """
    Attributes associated to the log (set up with the `attributes` argument of *e.g.*
    [info](@yw-nav-meth:youwol.utils.context.Context.info)).
    """
    context_id: str
    """
    The context ID that was used to generated this entry.
    """
    parent_context_id: str | None
    """
    The parent context ID that was used to generated this entry.
    """

    trace_uid: str | None
    """
    Trace ID (*i.e.*  root context ID).
    """

    timestamp: float
    """
    Timestamp: time in second since EPOC.
    """

    def dict(self):
        return {
            "level": self.level.name,
            "attributes": self.attributes,
            "labels": self.labels,
            "text": self.text,
            "data": self.data,
            "contextId": self.context_id,
            "parentContextId": self.parent_context_id,
            "timestamp": self.timestamp,
            "traceUid": self.trace_uid,
        }


DataType = Union[T, Callable[[], T], Callable[[], Awaitable[T]]]
"""
Type definition of context's data attribute.
"""


class ContextReporter(ABC):
    """
    Abstract class that implements log strategy (e.g. within terminal, file, REST call, *etc.*).
    """

    @abstractmethod
    async def log(self, entry: LogEntry):
        """
        Parameters:
            entry: the og entry to process
        """
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
    """
    Base class for context reporters using web sockets.
    """

    websockets_getter: Callable[[], List[WebSocket]]
    """
    Callback that provides a list of web socket channels to use.
    This function is evaluated each time [log](@yw-nav-meth:youwol.utils.context.WsContextReporter.log) is called.
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
                [websockets_getter](@yw-nav-attr:youwol.utils.context.WsContextReporter.websockets_getter)
            mute_exceptions: see
                [websockets_getter](@yw-nav-attr:youwol.utils.context.WsContextReporter.mute_exceptions)
        """
        self.websockets_getter = websockets_getter
        self.mute_exceptions = mute_exceptions

    async def log(self, entry: LogEntry):
        """
        Send a [LogEntry](@yw-nav-class:youwol.utils.context.LogEntry) in the web-socket channels.

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


StringLike = Any

HeadersFwdSelector = Callable[[list[str]], list[str]]
"""
A selector function for headers: it takes a list of header's keys in argument, and return the selected keys from it.
"""


TEnvironment = TypeVar("TEnvironment")
"""
Generic type parameter for the [Context](@yw-nav-class:youwol.utils.context.Context) class.

It defines contextual information known at 'compile' time.
"""


@dataclass(frozen=True)
class Context(Generic[TEnvironment]):
    """
    Context objects serves at tracing the execution flow within python code and logs information as well as
    propagating contextual information.

    This class has a generic type parameter `TEnvironment`, defining the type of
    [env](@yw-nav-attr:youwol.utils.context.Context.env), a 'compile-time' resolved contextual information.
    """

    env: TEnvironment | None = None
    """
    This attribute is a typed, static data point established during the creation of the root context and is
    accessible to all its child contexts.

    Being 'static' implies that the attribute's value and structure are predetermined at 'compile' time.
    It's generally better -if possible- to store information in this attribute rather than relying on dynamic
    fields like `labels`, `attributes`, or `data`.
    """

    logs_reporters: list[ContextReporter] = field(default_factory=list)
    """
    The list of reporters used to log information. Information are not meant to vehicle logic.
    See the attribute `data_reporters` for log that actually conveys logic related data.
    """

    data_reporters: list[ContextReporter] = field(default_factory=list)
    """
    The list of reporters used to log data.
    """

    request: Request | None = None
    """
    If the context was initiated with an incoming request (using the method
    [start_ep](@yw-nav-meth:youwol.utils.context.Context.start_ep)), it stores the original
    [Request](https://fastapi.tiangolo.com/reference/request/) object.
    """

    uid: str = "root"
    """
    Context UID.
    """

    parent_uid: str | None = None
    """
    Parent's context UID.
    """

    trace_uid: str | None = None
    """
    The root parent's UID of the context, it is the `trace_uid` of the request if applicable.
    """

    with_data: dict[str, DataType] = field(default_factory=dict)

    with_attributes: dict[str, TContextAttr] = field(default_factory=dict)
    """
    A JSON like datastructure that gets forwarded to children context.
    """

    with_labels: list[str] = field(default_factory=list)
    """
    A list of tags that gets forwarded to children context.
    """

    with_headers: dict[str, str] = field(default_factory=dict)
    """
    Defines some headers that will gets forwarded to children context and retrieved using the method
    [headers](@yw-nav-attr:youwol.utils.context.Context.headers).
    """

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
    ) -> ScopedContext[TEnvironment]:
        """
        Function to start a child context bound to an execution scope.

        Parameters:
            action: a title of the context
            with_labels: labels to add to the context and its children
            with_attributes: attributes to add to the context and its children
            with_headers: additional headers to add to the context and its children
            with_cookies: additional cookies to add to the context and its children
            with_reporters: additional reporters that are included in the context and its children
            on_enter: function to execute at context's start
            on_exit: function to execute at context's exit
            on_exception: function to execute if an exception is raised during the context's scope
            with_data: deprecated

        Return:
            new child

        **Example:**

        ```python
        async def foo(
            project: Project,
            flow_id: str,
            step: PipelineStep,
            context: Context,
        ):
            async with context.start(
                action="foo",
                with_attributes={
                    "projectId": project.id,
                    "flowId": flow_id,
                    "stepId": step.id
                },
            ) as ctx:
                pass
        ```
        """

        with_attributes = with_attributes or {}
        with_labels = with_labels or []
        with_data = with_data or {}
        logs_reporters = (
            self.logs_reporters
            if with_reporters is None
            else self.logs_reporters + with_reporters
        )

        return ScopedContext[TEnvironment](
            action=action,
            env=self.env,
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
        """
        Static method to start a context when reaching an end point.

        Parameters:
            request: initiating request.
            action: a custom title of the context, if not provided the request's URL
            with_labels: labels to add to the context and its children
            with_attributes: attributes to add to the context and its children
            with_reporters: additional reporters that are included in the context and its children
            on_enter: function to execute at context's start
            on_exit: function to execute at context's exit
            body: body of the request (deprecated)
            response: response of the request (deprecated)

        Return:
            The new scoped context.

        **Example:**

        ```python
        @router.get("/status", response_model=ProjectsLoadingResults, summary="status")
        async def status(request: Request):

            async with Context.start_ep(
                request=request, with_reporters=[LogsStreamer()]
            ) as ctx:
                response = await ProjectLoader.refresh(ctx)
                await ctx.send(response)
                return response
        ```
        """

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
        """
        Send data.

        Parameters:
            data: data to send
            labels: additional labels associated
        """

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
        """
        Log information with severity [Debug](@yw-nav-att:youwol.utils.context.LogLevel.DEBUG).

        Parameters:
            text: text of the log
            labels: additional labels associated
            data: data to associate
        """
        await self.log(level=LogLevel.DEBUG, text=text, labels=labels, data=data)

    async def info(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        """
        Log information with severity [Info](@yw-nav-att:youwol.utils.context.LogLevel.INFO).

        Parameters:
            text: text of the log
            labels: additional labels associated
            data: data to associate
        """
        await self.log(level=LogLevel.INFO, text=text, labels=labels, data=data)

    async def warning(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        """
        Log information with severity [Warning](@yw-nav-att:youwol.utils.context.LogLevel.WARNING).

        Parameters:
            text: text of the log
            labels: additional labels associated
            data: data to associate
        """
        await self.log(level=LogLevel.WARNING, text=text, labels=labels, data=data)

    async def error(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        """
        Log information with severity [Error](@yw-nav-att:youwol.utils.context.LogLevel.ERROR).

        Parameters:
            text: text of the log
            labels: additional labels associated
            data: data to associate
        """
        await self.log(level=LogLevel.ERROR, text=text, labels=labels, data=data)

    async def failed(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
    ):
        """
        Log information with severity [ERROR](@yw-nav-att:youwol.utils.context.LogLevel.ERROR) and
        the tag `FAILED` to indicate that an unrecoverable failure in the encapsulated function happened
        even if no exception has been raised.

        Note:
            It is most often preferred to raise an exception.

        Parameters:
            text: text of the log
            labels: additional labels associated
            data: data to associate
        """
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
        """
        Log information with severity [Info](@yw-nav-att:youwol.utils.context.LogLevel.INFO) and
        the tag `FUTURE` to indicate that an asynchronous task has been scheduled (and not awaited).

        Parameters:
            text: text of the log
            future: if provided, a log entry will also be added when the future complete (or is canceled)
            labels: additional labels associated
            data: data to associate
        """

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

    def headers(self, from_req_fwd: HeadersFwdSelector = lambda _keys: []) -> AnyDict:
        """
        Return the headers associated to the context.

        Parameters:
            from_req_fwd: selector returning the list of header's keys to forward given the header's keys
        of the initiating request of the context.

        Return:
            headers with all contribution (from YouWol, from original request & from eventual contribution at each
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
        """

        Return:
            The cookie associated to the original request.
            If the context has not been generated from a request, return `{}`
        """
        cookies = self.request.cookies if self.request else {}
        return cookies


CallableBlock = Callable[[Context], Union[Awaitable, None]]
"""
Signature for [scoped context](@yw-nav-class:youwol.utils.context.ScopedContext)'s callable when
entering or exiting a block.
"""

CallableBlockException = Callable[[Exception, Context], Union[Awaitable, None]]
"""
Signature for [scoped context](@yw-nav-class:youwol.utils.context.ScopedContext)'s callable when
exiting a block with exception.
"""

LabelsGetter = Callable[[], set[str]]
"""
Type definition of a Label definition, used in [ContextFactory](@yw-nav-class:youwol.utils.context.ContextFactory).
"""


@dataclass(frozen=True)
class ScopedContext(Generic[TEnvironment], Context[TEnvironment]):
    """
    A context with lifecycle management logic (implementing async context manager API from python: `__aenter__`
    and `__aexit__`).

    `ScopedContext` are created using the method [start](@yw-nav-meth:youwol.utils.context.Context.start) and
    [start_ep](@yw-nav-meth:youwol.utils.context.Context.start_ep).
    """

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
                    "detail": (
                        exc.detail
                        if isinstance(exc, HTTPException)
                        else "No detail available"
                    ),
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


@dataclass(frozen=True)
class ProxiedBackendCtxEnv:
    """
    Type of the [Context.env](@yw-nav-attr:youwol.utils.context.Context.env) attribute for
    [ProxiedBackendContext](@yw-nav-glob:youwol.utils.context.ProxiedBackendContext)
    specialization of [Context](@yw-nav-class:youwol.utils.context.Context).

    """

    assets_gateway: AssetsGatewayClient
    """
    HTTP client.
    """
    sessions_storage: CdnSessionsStorageClient
    """
    HTTP client.
    """


ProxiedBackendContext = Context[ProxiedBackendCtxEnv]
"""
Specialization of [Context](@yw-nav-class:youwol.utils.context.Context) for detached backends
(running on specific port) proxied by the local youwol server.
"""


class ContextFactory:
    """
    Factory to create root contexts.
    """

    with_static_data: dict[str, DataType] = {}
    """
    The data that will be associated to all root contexts created.
    """

    with_static_labels: dict[str, LabelsGetter] = {}
    """
    The labels that will be associated to all root contexts created.
    """

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

    @staticmethod
    def proxied_backend_context(request: Request, **kwargs) -> ProxiedBackendContext:
        """
        Initializes a [Context](@yw-nav-class:youwol.utils.context.Context) instance from
        a request for (python) backends running on specific port & proxied using a
        [RedirectSwitch](@yw-nav-class:youwol.app.environment.models.models_config.RedirectSwitch).

         It usually starts the implementation of an endpoint, e.g.:

        ```python
        @app.get("/hello-world")
        async def hello_world(request: Request):
            async with ContextFactory.proxied_backend_context(request).start(
                action="/hello-world"
            ) as ctx:
                await ctx.info("Hello world")
                return JSONResponse({"endpoint": "/hello-world"})
        ```

        The instance created:
        *  defines the context's `env` attribute as
         [ProxiedBackendCtxEnv](@yw-nav-class:youwol.utils.context.ProxiedBackendCtxEnv).
        *  defines the context's `logs_reporter` attribute using a reporter that forward log's entries to the youwol
        local server end point [post_log](@yw-nav-func:youwol.app.routers.system.router.post_logs).
        In a standard configuration of youwol, they are then stored in memory and can be browsed through the
        developer portal application.
        *  defines the context's `data_reporter` attribute using a reporter that forward log's entries to the youwol
         local server end point [post_data](@yw-nav-func:youwol.app.routers.system.router.post_data).
        In a standard configuration of youwol, they are then emitted through the `/ws-data` web-socket channel
        of youwol.
        This serves as constructing [FuturesResponse](@yw-nav-class:youwol.utils.utils_requests.FuturesResponse) to
        provide observable like response emitting multiple items asynchronously.

        Parameters:
            request: Incoming request.

        Return:
            A type specialisation of [Context](@yw-nav-class:youwol.utils.context.Context) with
            [ProxiedBackendCtxEnv](@yw-nav-class:youwol.utils.context.ProxiedBackendCtxEnv) generic parameter.
        """
        static_data = ContextFactory.with_static_data or {}
        static_labels = ContextFactory.with_static_labels or {}
        with_data = kwargs if not static_data else {**static_data, **kwargs}
        with_labels = [label for getter in static_labels.values() for label in getter()]

        py_youwol_port = request.headers[YouwolHeaders.py_youwol_port]

        class PyYwReporter(ContextReporter):
            request: Request
            url: str
            channel: Literal["logs", "data"]

            def __init__(self, channel: Literal["logs", "data"]):
                super().__init__()
                self.request = request
                self.channel = channel
                self.url = (
                    f"http://localhost:{py_youwol_port}/admin/system/{self.channel}"
                )

            async def log(self, entry: LogEntry):
                body = {self.channel: [entry.dict()]}
                headers: Mapping[str, str] = {
                    YouwolHeaders.trace_id: entry.trace_uid or "",
                    YouwolHeaders.correlation_id: entry.context_id or "",
                }
                async with aiohttp.ClientSession(
                    cookies=self.request.cookies, headers=headers
                ) as session:
                    t = await session.post(url=self.url, json=body)
                    t.close()

        logs_reporter = PyYwReporter(channel="logs")
        data_reporter = PyYwReporter(channel="data")
        http_clients = ProxiedBackendCtxEnv(
            assets_gateway=AssetsGatewayClient(
                url_base=f"http://localhost:{py_youwol_port}/api/assets-gateway",
                request_executor=AioHttpExecutor(),
            ),
            sessions_storage=CdnSessionsStorageClient(
                url_base=f"http://localhost:{py_youwol_port}/api/cdn-sessions-storage",
                request_executor=AioHttpExecutor(),
            ),
        )
        return Context(
            request=request,
            env=http_clients,
            logs_reporters=[logs_reporter],
            data_reporters=[data_reporter],
            with_labels=with_labels,
            with_data={"py_youwol_port": py_youwol_port, **with_data},
            parent_uid=YouwolHeaders.get_correlation_id(request),
            trace_uid=YouwolHeaders.get_trace_id(request),
            uid=YouwolHeaders.get_correlation_id(request) or "root",
        )


class DeployedContextReporter(ContextReporter):
    """
    This [ContextReporter](@yw-nav-class: youwol.utils.context.ContextReporter) logs into the standard
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
    This [ContextReporter](@yw-nav-class:youwol.utils.context.ContextReporter) logs into the standard
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
    This [ContextReporter](@yw-nav-class: youwol.utils.context.ContextReporter) send logs through
    an API call to a running youwol server in localhost.

    It uses a POST request at `http://localhost:{self.py_youwol_port}/admin/system/logs` with provided headers.

    See [post_logs](@yw-nav-func:youwol.app.routers.system.post_logs).
    """

    py_youwol_port: int
    """
    Port used on localhost to execute the POST request of the log.
    """
    headers: dict[str, str]
    """
    Headers associated to the POST request of the log.
    """

    def __init__(self, py_youwol_port: int, headers: Optional[dict[str, str]] = None):
        """
        Set the class's attributes.

        Parameters:
            py_youwol_port: see
                [py_youwol_port](@yw-nav-attr:youwol.utils.context.PyYouwolContextReporter.py_youwol_port)
            headers: see
                [headers](@yw-nav-attr:youwol.utils.context.PyYouwolContextReporter.headers)
        """
        super().__init__()
        self.py_youwol_port = py_youwol_port
        self.headers = headers or {}

    async def log(self, entry: LogEntry):
        """
        Send the log to a py-youwol running server using provided
        [port](@yw-nav-attr:youwol.utils.context.PyYouwolContextReporter.py_youwol_port) and
        [headers](@yw-nav-attr:youwol.utils.context.PyYouwolContextReporter.headers).

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

    They are created from the context using [Context.start](@yw-nav-meth:youwol.utils.context.Context.start) or
    [Context.start_ep](@yw-nav-meth:youwol.utils.context.Context.start_ep).
    """

    leaf_logs: list[LogEntry] = []
    """
    The list of all 'leaf' logs: those associated to a simple log
     (e.g. [Context.info](@yw-nav-meth:youwol.utils.context.Context.info)).
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
