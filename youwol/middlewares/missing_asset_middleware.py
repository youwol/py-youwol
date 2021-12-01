import asyncio
from asyncio import Queue
from typing import List, Mapping

from asset_auto_download import enqueue_asset

from configuration.youwol_configuration import yw_config
from context import Context
from errors import HTTPResponseException
from middlewares.redirect import redirect_api_remote

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from web_socket import WebSocketsCache


class MissingAssetsMiddleware(BaseHTTPMiddleware):

    def __init__(self,
                 app: ASGIApp,
                 assets_kind: List[str],
                 download_queue: Queue[(str, Context, Mapping[str, str])],
                 download_event_loop
                 ) -> None:
        super().__init__(app)
        self.download_queue = download_queue
        self.assets_kind = assets_kind
        self.download_event_loop = download_event_loop

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        try:
            config = await yw_config()
        except HTTPResponseException as e:
            return e.httpResponse

        context = Context(
            web_socket=WebSocketsCache.api_gateway,
            config=config,
            request=request
            )

        resp = await call_next(request)

        if any(f'/api/assets-gateway/raw/{kind}' in request.url.path for kind in self.assets_kind)\
                and request.method == "GET":

            if resp.status_code == 404:
                resp = await redirect_api_remote(request)
                headers = {"Authorization": request.headers.get("authorization")}
                asyncio.run_coroutine_threadsafe(
                    enqueue_asset(self.download_queue, request.url.path, context, headers),
                    self.download_event_loop
                    )
                return resp

        return resp
