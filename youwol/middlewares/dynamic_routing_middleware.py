from typing import List

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.configuration.models_dispatch import AbstractDispatch
from youwol.context import Context
from youwol.web_socket import WebSocketsCache
from youwol.environment.youwol_environment import yw_config


class DynamicRoutingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp,
                 dynamic_dispatch_rules: List[AbstractDispatch]
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
            match = await dispatch.apply(request, call_next, context)
            if match:
                return match

        return await call_next(request)
