# future
from __future__ import annotations

# standard library
import asyncio
import functools
import time
import traceback
import uuid

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from types import TracebackType

# typing
from typing import Generic, Literal, TypeVar, Union, cast

# third parties
import aiohttp

from fastapi import HTTPException
from pydantic import BaseModel
from starlette.requests import Request

# relative
from ..clients.assets_gateway.assets_gateway import AssetsGatewayClient
from ..clients.cdn_sessions_storage import CdnSessionsStorageClient
from ..clients.request_executor import AioHttpExecutor
from ..types import AnyDict
from ..utils import YouwolHeaders, generate_headers_downstream, to_json
from .models import (
    ContextReporter,
    DataType,
    HeadersFwdSelector,
    JsonLike,
    Label,
    LabelsGetter,
    LogEntry,
    LogLevel,
    ProxiedBackendCtxEnv,
    StringLike,
    TContextAttr,
)

T = TypeVar("T")
"""
Generic type parameter for the [Context](@yw-nav-class:Context) class.

It defines contextual information known at 'compile' time.
"""


@dataclass(frozen=True)
class Context(Generic[T]):
    """
    Context objects serves at tracing the execution flow within python code and logs information as well as
    propagating contextual information.

    This class has a generic type parameter `TEnvironment`, defining the type of
    [env](@yw-nav-attr:Context.env), a 'compile-time' resolved contextual information.
    """

    env: T | None = None
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
    [start_ep](@yw-nav-meth:Context.start_ep)), it stores the original
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
    [headers](@yw-nav-attr:Context.headers).
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
    ) -> ScopedContext[T]:
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

        return ScopedContext[T](
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
        attributes: dict[str, TContextAttr] | None = None,
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
        attributes = {**self.with_attributes, **(attributes or {})}
        entry = LogEntry(
            level=level,
            text=text,
            data=json_data,
            labels=labels,
            attributes=attributes,
            context_id=self.uid,
            parent_context_id=self.parent_uid,
            trace_uid=self.trace_uid,
            timestamp=time.time() * 1e6,
        )
        if level == LogLevel.DATA:
            await asyncio.gather(*[logger.log(entry) for logger in self.data_reporters])

        await asyncio.gather(*[logger.log(entry) for logger in self.logs_reporters])

    async def send(
        self,
        data: BaseModel,
        labels: list[StringLike] | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        """
        Send data.

        Parameters:
            data: Data.
            labels: Additional labels.
            attributes: Additional attributes.
        """

        labels = labels or []
        await self.log(
            level=LogLevel.DATA,
            text=f"Send data '{data.__class__.__name__}'",
            labels=[data.__class__.__name__, *labels],
            attributes=attributes,
            data=data,
        )

    async def debug(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        """
        Log information with severity [Debug](@yw-nav-att:youwol.utils.context.LogLevel.DEBUG).

        Parameters:
            text: Text of the log.
            data: Associated data.
            labels: Additional labels.
            attributes: Additional attributes.
        """
        await self.log(
            level=LogLevel.DEBUG,
            text=text,
            labels=labels,
            attributes=attributes,
            data=data,
        )

    async def info(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        """
        Log information with severity [Info](@yw-nav-att:youwol.utils.context.LogLevel.INFO).

        Parameters:
            text: Text of the log.
            data: Associated data.
            labels: Additional labels.
            attributes: Additional attributes.
        """
        await self.log(
            level=LogLevel.INFO,
            text=text,
            labels=labels,
            attributes=attributes,
            data=data,
        )

    async def warning(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        """
        Log information with severity [Warning](@yw-nav-att:youwol.utils.context.LogLevel.WARNING).

        Parameters:
            text: Text of the log.
            data: Associated data.
            labels: Additional labels.
            attributes: Additional attributes.
        """
        await self.log(
            level=LogLevel.WARNING,
            text=text,
            labels=labels,
            attributes=attributes,
            data=data,
        )

    async def error(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        """
        Log information with severity [Error](@yw-nav-att:youwol.utils.context.LogLevel.ERROR).

        Parameters:
            text: Text of the log.
            data: Associated data.
            labels: Additional labels.
            attributes: Additional attributes.
        """
        await self.log(
            level=LogLevel.ERROR,
            text=text,
            labels=labels,
            attributes=attributes,
            data=data,
        )

    async def failed(
        self,
        text: str,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        """
        Log information with severity [ERROR](@yw-nav-att:youwol.utils.context.LogLevel.ERROR) and
        the tag `FAILED` to indicate that an unrecoverable failure in the encapsulated function happened
        even if no exception has been raised.

        Note:
            It is most often preferred to raise an exception.

        Parameters:
            text: Text of the log.
            data: Associated data.
            labels: Additional labels.
            attributes: Additional attributes.
        """
        labels = labels or []
        await self.log(
            level=LogLevel.ERROR,
            text=text,
            labels=[Label.FAILED, *labels],
            attributes=attributes,
            data=data,
        )

    async def future(
        self,
        text: str,
        future: asyncio.Future | None = None,
        labels: list[StringLike] | None = None,
        data: JsonLike | None = None,
        attributes: dict[str, TContextAttr] | None = None,
    ):
        """
        Log information with severity [Info](@yw-nav-att:youwol.utils.context.LogLevel.INFO) and
        the tag `FUTURE` to indicate that an asynchronous task has been scheduled (and not awaited).

        Parameters:
            text: Text of the log.
            future: If provided, a log entry will also be added when the future complete (or is canceled).
            labels: Additional labels.
            data: Associated data.
            attributes: Additional attributes.
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
                        attributes=attributes,
                        data=data,
                    )
                )
            elif task.exception() is not None:
                asyncio.ensure_future(
                    self.log(
                        level=LogLevel.ERROR,
                        text=f"Future '{text}' resolved with exception",
                        labels=[Label.FUTURE_FAILED, *labels],
                        attributes=attributes,
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
                        attributes=attributes,
                        data=data,
                    )
                )

        future.add_done_callback(done_callback)

    async def get(self, att_name: str, _object_type: type[T]) -> T:
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
Signature for [scoped context](@yw-nav-class:ScopedContext)'s callable when
entering or exiting a block.
"""

CallableBlockException = Callable[[Exception, Context], Union[Awaitable, None]]
"""
Signature for [scoped context](@yw-nav-class:ScopedContext)'s callable when
exiting a block with exception.
"""


@dataclass(frozen=True)
class ScopedContext(Generic[T], Context[T]):
    """
    A context with lifecycle management logic (implementing async context manager API from python: `__aenter__`
    and `__aexit__`).

    `ScopedContext` are created using the method [start](@yw-nav-meth:Context.start) and
    [start_ep](@yw-nav-meth:Context.start_ep).
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


ProxiedBackendContext = Context[ProxiedBackendCtxEnv]
"""
Specialization of [Context](@yw-nav-class:Context) for detached backends
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
    def get_instance(
        with_labels: list[str] | None = None,
        with_attributes: dict[str, TContextAttr] | None = None,
        **kwargs,
    ) -> Context:
        static_data = ContextFactory.with_static_data or {}
        static_labels = ContextFactory.with_static_labels or {}
        with_data = kwargs if not static_data else {**static_data, **kwargs}
        with_labels = [
            *[label for getter in static_labels.values() for label in getter()],
            *(with_labels or []),
        ]
        with_attributes = with_attributes or {}
        return Context(
            with_labels=with_labels,
            with_data=with_data,
            with_attributes=with_attributes,
            **kwargs,
        )

    @staticmethod
    def proxied_backend_context(request: Request, **kwargs) -> ProxiedBackendContext:
        """
        Initializes a [Context](@yw-nav-class:Context) instance from
        a request for (python) backends running on specific port & proxied using a
        [RedirectSwitch](@yw-nav-class:RedirectSwitch).

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
         [ProxiedBackendCtxEnv](@yw-nav-class:ProxiedBackendCtxEnv).
        *  defines the context's `logs_reporter` attribute using a reporter that forward log's entries to the youwol
        local server end point [post_log](@yw-nav-func:post_logs).
        In a standard configuration of youwol, they are then stored in memory and can be browsed through the
        developer portal application.
        *  defines the context's `data_reporter` attribute using a reporter that forward log's entries to the youwol
         local server end point [post_data](@yw-nav-func:post_data).
        In a standard configuration of youwol, they are then emitted through the `/ws-data` web-socket channel
        of youwol.
        This serves as constructing [FuturesResponse](@yw-nav-class:FuturesResponse) to
        provide observable like response emitting multiple items asynchronously.

        Parameters:
            request: Incoming request.

        Return:
            A type specialisation of [Context](@yw-nav-class:Context) with
            [ProxiedBackendCtxEnv](@yw-nav-class:ProxiedBackendCtxEnv) generic parameter.
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
