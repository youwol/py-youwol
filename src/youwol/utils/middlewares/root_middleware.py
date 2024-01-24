# standard library
import uuid

# typing
from typing import Optional

# third parties
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Youwol utilities
from youwol.utils import YouwolHeaders
from youwol.utils.context import ContextFactory, ContextReporter, Label
from youwol.utils.request_info_factory import request_info


class RootMiddleware(BaseHTTPMiddleware):
    """
    The first Middleware intercepting the request.

    Its purpose is mostly to set up the initial [context](@yw-nav-class:youwol.utils.context.Context),
    from the method [get_context](@yw-nav-meth:youwol.utils.middlewares.root_middleware.RootMiddleware.get_context)

    The context created here is then propagated through the middlewares stack up to the end-point destination.
    """

    ctx_logger: ContextReporter

    black_list = ["authorization"]

    def __init__(
        self,
        app: ASGIApp,
        logs_reporter: ContextReporter,
        data_reporter: Optional[ContextReporter],
        dispatch: Optional[DispatchFunction] = None,
        **_,
    ) -> None:
        """
        Constructor.

        Parameters:
            app: The FastAPI application
            logs_reporter: The initial [logs reporter](@yw-nav-attr:youwol.utils.context.Context.logs_reporters)
                used by the context created at incoming request and propagated up to the target end-point.
            data_reporter: The initial [data reporter](@yw-nav-attr:youwol.utils.context.Context.data_reporters)
                used by the context created at incoming request and propagated up to the target end-point.
            dispatch: Optional, forwarded to the parent starlette's `BaseHTTPMiddleware`.

        """
        super().__init__(app, dispatch)
        self.logs_reporters = [logs_reporter]
        self.data_reporters = [data_reporter] if data_reporter else []

    def get_context(self, request: Request):
        """
        Set up the initial context:
            *  retrieve eventual `trace_id` and `correlation_id` from the incoming request's headers to set
            the  [context.trace_uid](@yw-nav-attr:youwol.utils.context.Context.trace_uid) and
             [context.parent_uid](@yw-nav-attr:youwol.utils.context.Context.parent_uid) respectively.
             See [YouwolHeaders.get_trace_id](@yw-nav-meth:youwol.utils.utils.YouwolHeaders.get_trace_id) and
            [YouwolHeaders.get_correlation_id](@yw-nav-meth:youwol.utils.utils.YouwolHeaders.get_correlation_id).
            *  set up the [ContextReporter](@yw-nav-class:youwol.utils.context.ContextReporter) for both logs and data.

        Parameters:
            request: incoming request

        """
        root_id = YouwolHeaders.get_correlation_id(request)
        trace_id = YouwolHeaders.get_trace_id(request)
        return ContextFactory.get_instance(
            request=request,
            logs_reporters=self.logs_reporters,
            data_reporters=self.data_reporters,
            parent_uid=root_id,
            trace_uid=trace_id if trace_id else str(uuid.uuid4()),
            uid=root_id if root_id else "root",
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Log information w/ incoming request, dispatch the incoming request, log information w/ response.

        Parameters:
            request: incoming request
            call_next: trigger function of the next middleware

        Return:
            HTTP Response
        """
        context = self.get_context(request=request)
        info = request_info(request)

        async with context.start(
            action=info.message,
            with_attributes={**info.attributes, "traceId": context.trace_uid},
            with_labels=[Label.API_GATEWAY, *info.labels],
        ) as ctx:
            await ctx.info(
                text="Root middleware => incoming request",
                data={
                    "url": request.url.path,
                    "method": request.method,
                    "headers": {
                        k: v if k.lower() not in self.black_list else "**black-listed**"
                        for k, v in request.headers.items()
                    },
                },
            )
            response = await call_next(request)

            await ctx.info(
                f"{request.method} {request.url.path}: {response.status_code}",
                data={"headers": dict(response.headers.items())},
            )
            # Even for a very broad definition of failure, there are many « not failure »
            # status code (i.e. 204,308, etc.)
            # Only 4xx (client error) and 5xx (server error) are considered failure
            if response.status_code >= 400:
                await ctx.failed(f"Request resolved to error {response.status_code}")

            if response.status_code == 202:
                await ctx.future("202 : Request accepted, status not resolved yet")

            response.headers[YouwolHeaders.trace_id] = ctx.trace_uid
            response.headers["cross-origin-opener-policy"] = "same-origin"
            response.headers["cross-origin-embedder-policy"] = "require-corp"
            return response
