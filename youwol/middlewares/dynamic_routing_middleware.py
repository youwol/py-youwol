from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from context import Context
from web_socket import WebSocketsCache
from youwol.configuration.youwol_configuration import yw_config


class DynamicRoutingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp,
                 dynamic_dispatch_rules
                 ) -> None:
        super().__init__(app)
        self.dynamic_dispatch_rules = dynamic_dispatch_rules

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        config = await yw_config()
        context = Context(
            web_socket=WebSocketsCache.system,
            config=config,
            request=request
            )
        for dispatch in self.dynamic_dispatch_rules:
            match = await dispatch.is_matching(request, context)
            if match:
                return await dispatch.apply(request=request, call_next=call_next, context=context)

        return await call_next(request)
