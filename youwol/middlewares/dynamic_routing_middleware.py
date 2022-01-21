from typing import List

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.middlewares.models_dispatch import AbstractDispatch


class DynamicRoutingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp,
                 dynamic_dispatch_rules: List[AbstractDispatch],
                 disabling_header: str
                 ) -> None:
        super().__init__(app)
        self.dynamic_dispatch_rules = dynamic_dispatch_rules
        self.disabling_header = disabling_header

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        async with request.state.context.start(action="attempt dynamic dispatches") as ctx:
            if request.headers.get(self.disabling_header, False):
                ctx.info(text="Dynamic dispatch disabled")
                request.state.context = ctx
                return await call_next(request)

            for dispatch in self.dynamic_dispatch_rules:
                match = await dispatch.apply(request, call_next, ctx)
                if match:
                    return match
            ctx.info(text="No dynamic dispatch match")

            ctx.info(text="Request proceed to normal destination", data={"url": request.url.path})
            request.state.context = ctx
            return await call_next(request)
