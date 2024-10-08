# standard library
import uuid

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

    Its purpose is mostly to set up the initial :class:`context <youwol.utils.context.context.Context>`,
    from the method :meth:`get_context <youwol.utils.middlewares.root_middleware.RootMiddleware.get_context>`

    The context created here is then propagated through the middlewares stack up to the end-point destination.
    """

    ctx_logger: ContextReporter

    black_list = ["authorization"]

    def __init__(
        self,
        app: ASGIApp,
        logs_reporter: ContextReporter,
        data_reporter: ContextReporter | None,
        dispatch: DispatchFunction | None = None,
        **_,
    ) -> None:
        """
        Constructor.

        Parameters:
            app: The FastAPI application
            logs_reporter: The initial :attr:`logs reporter <youwol.utils.context.context.Context.logs_reporters>`
                used by the context created at incoming request and propagated up to the target end-point.
            data_reporter: The initial :attr:`data reporter <youwol.utils.context.context.Context.data_reporters>`
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
            the  :attr:`context.trace_uid <youwol.utils.context.context.Context.trace_uid>` and
             :attr:`context.parent_uid <youwol.utils.context.context.Context.parent_uid>` respectively.
             See :meth:`YouwolHeaders.get_trace_id <youwol.utils.utils.YouwolHeaders.get_trace_id>` and
            :meth:`YouwolHeaders.get_correlation_id <youwol.utils.utils.YouwolHeaders.get_correlation_id>`.
            *  set up the :class:`ContextReporter <youwol.utils.context.models.ContextReporter>` for both logs and data.

        Parameters:
            request: incoming request

        """
        root_id = YouwolHeaders.get_correlation_id(request)
        trace_id = YouwolHeaders.get_trace_id(request)
        with_labels = YouwolHeaders.get_trace_labels(request)
        with_attributes = YouwolHeaders.get_trace_attributes(request)

        context = ContextFactory.get_instance(
            request=request,
            with_labels=with_labels,
            with_attributes=with_attributes,
            logs_reporters=self.logs_reporters,
            data_reporters=self.data_reporters,
            parent_uid=root_id,
            trace_uid=trace_id if trace_id else str(uuid.uuid4()),
            uid=root_id if root_id else "root",
        )
        return context

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Log information w/ incoming request, dispatch the incoming request, log information w/ response.

        Parameters:
            request: incoming request
            call_next: trigger function of the next middleware

        Returns:
            HTTP Response
        """
        context = self.get_context(request=request)
        info = request_info(request)

        async with context.start_middleware(
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
