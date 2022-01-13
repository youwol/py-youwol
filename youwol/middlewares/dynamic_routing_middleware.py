from typing import List

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.web_socket import WebSocketsStore
from youwol_utils.context import ContextFactory


class DynamicRoutingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp,
                 dynamic_dispatch_rules: List[AbstractDispatch]
                 ) -> None:
        super().__init__(app)
        self.dynamic_dispatch_rules = dynamic_dispatch_rules

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        context = ContextFactory.get_instance(
            request=request,
            web_socket=WebSocketsStore.userChannel
        )
        for dispatch in self.dynamic_dispatch_rules:
            match = await dispatch.apply(request, call_next, context)
            if match:
                return match

        return await call_next(request)
