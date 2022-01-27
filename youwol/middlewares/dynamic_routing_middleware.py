from typing import List

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol_utils.context import Context, Label


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

        async with Context.from_request(request).start(
                action="attempt dynamic dispatches",
                with_labels=[Label.MIDDLEWARE]
        ) as ctx:
            if request.headers.get(self.disabling_header, False):
                ctx.warning(text="Dynamic dispatch disabled")
                return await call_next(request)

            for dispatch in self.dynamic_dispatch_rules:
                match = await dispatch.apply(request, call_next, ctx)
                if match:
                    return match
            await ctx.info(text="No dynamic dispatch match")

            await ctx.info(text="Request proceed to normal destination", data={"url": request.url.path})

            return await call_next(request)
