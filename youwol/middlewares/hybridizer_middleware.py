from typing import List

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.middlewares.local_cloud_hybridizers.abstract_local_cloud_dispatch import AbstractLocalCloudDispatch
from youwol_utils import YouWolException, youwol_exception_handler
from youwol_utils.context import Context, Label


class LocalCloudHybridizerMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp,
                 dynamic_dispatch_rules: List[AbstractLocalCloudDispatch],
                 disabling_header: str
                 ) -> None:
        super().__init__(app)
        self.dynamic_dispatch_rules = dynamic_dispatch_rules
        self.disabling_header = disabling_header

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        async with Context.from_request(request).start(
                action="attempt hybrid local/cloud dispatches",
                with_labels=[Label.MIDDLEWARE]
        ) as ctx:
            if request.headers.get(self.disabling_header, "false") == "true":
                await ctx.warning(text="Dynamic dispatch disabled")
                return await call_next(request)

            for dispatch in self.dynamic_dispatch_rules:
                try:
                    match = await dispatch.apply(request, call_next, ctx)
                    if match:
                        return match
                except YouWolException as e:
                    return await youwol_exception_handler(request, e)

            await ctx.info(text="No dynamic dispatch match")

            await ctx.info(text="Request proceed to normal destination", data={"url": request.url.path})

            return await call_next(request)
