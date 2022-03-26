import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol_utils import YouwolHeaders
from youwol_utils.context import ContextFactory, Context, ContextLogger, Label
from youwol_utils.request_info_factory import request_info


class RootMiddleware(BaseHTTPMiddleware):

    ctx_logger: ContextLogger

    black_list = [
        "authorization"
    ]

    def __init__(
            self,
            app: ASGIApp,
            ctx_logger: ContextLogger,
            dispatch: DispatchFunction = None,
            **_
    ) -> None:
        super().__init__(app, dispatch)
        self.ctx_logger = ctx_logger

    def get_context(self, request: Request):

        root_id = YouwolHeaders.get_correlation_id(request)
        trace_id = YouwolHeaders.get_trace_id(request)
        with_data = ContextFactory.with_static_data or {}
        return Context(request=request,
                       loggers=[self.ctx_logger],
                       parent_uid=root_id,
                       trace_uid=trace_id if trace_id else str(uuid.uuid4()),
                       uid=root_id if root_id else 'root',
                       with_data=with_data)

    async def dispatch(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:

        context = self.get_context(request=request)
        info = request_info(request)

        async with context.start(
                action=info.message,
                with_attributes={**info.attributes, "traceId": context.trace_uid},
                with_labels=[Label.API_GATEWAY, *info.labels]
        ) as ctx:  # type: Context
            await ctx.info(
                text='incoming request',
                data={
                    'url': request.url.path,
                    'method': request.method,
                    'headers': {k: v if k.lower() not in self.black_list else "**black-listed**"
                                for k, v in request.headers.items()
                                }
                })
            response = await call_next(request)
            await ctx.info(f"{request.method} {request.url.path}: {response.status_code}")
            # Even for a very broad definition of failure, there are many « not failure »
            # status code (i.e. 204,308, etc.)
            # Only 4xx (client error) and 5xx (server error) are considered failure
            if response.status_code >= 400:
                await ctx.failed(f"Request resolved to error {response.status_code}")

            response.headers[YouwolHeaders.trace_id] = ctx.trace_uid

            return response
