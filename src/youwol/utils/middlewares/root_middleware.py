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
    ctx_logger: ContextReporter

    black_list = ["authorization"]

    def __init__(
        self,
        app: ASGIApp,
        logs_reporter: ContextReporter,
        data_reporter: Optional[ContextReporter],
        dispatch: DispatchFunction = None,
        **_,
    ) -> None:
        super().__init__(app, dispatch)
        self.logs_reporters = [logs_reporter]
        self.data_reporters = [data_reporter] if data_reporter else []

    def get_context(self, request: Request):
        root_id = YouwolHeaders.get_correlation_id(request)
        trace_id = YouwolHeaders.get_trace_id(request)
        muted_http_errors = YouwolHeaders.get_muted_http_errors(request)
        return ContextFactory.get_instance(
            request=request,
            logs_reporters=self.logs_reporters,
            data_reporters=self.data_reporters,
            parent_uid=root_id,
            trace_uid=trace_id if trace_id else str(uuid.uuid4()),
            muted_http_errors=muted_http_errors,
            uid=root_id if root_id else "root",
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
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

            response.headers[YouwolHeaders.trace_id] = ctx.trace_uid
            response.headers["cross-origin-opener-policy"] = "same-origin"
            response.headers["cross-origin-embedder-policy"] = "require-corp"
            return response
