import traceback
import sys

from aiohttp import ClientConnectorError

from middlewares.redirect import redirect_api_remote, redirect_api_local, redirect_get
from youwol.configuration.youwol_configuration import yw_config
from youwol.context import Context
from youwol.errors import HTTPResponseException
from youwol.routers.backends.utils import get_all_backends, BackEnd
from youwol.web_socket import WebSocketsCache

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


async def is_local_backend_alive(request: Request, backend: BackEnd) -> bool:
    headers = {"Authorization": request.headers.get("authorization")}
    try:
        await redirect_get(
            request=request,
            new_url=f"http://localhost:{backend.info.port}/{backend.pipeline.serve.health.strip('/')}",
            headers=headers)
        return True
    except ClientConnectorError:
        return False


class LiveServingBackendsMiddleware(BaseHTTPMiddleware):

    def __init__(self,
                 app: ASGIApp
                 ) -> None:
        super().__init__(app)

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

        if request.url.path.startswith('/remote/api'):
            return await redirect_api_remote(
                request=request,
                redirect_url=f"https://{config.selectedRemote}{request.url.path.split('/remote')[1]}")

        backends = await get_all_backends(context)
        backend = next((backend for backend in backends
                        if backend.target.basePath and request.url.path.startswith(backend.target.basePath)),
                       None)
        if not backend:
            return await call_next(request)

        running = await is_local_backend_alive(request=request, backend=backend)

        try:
            if running:
                return await redirect_api_local(request,
                                                backend.info.name,
                                                request.url.path.split(backend.target.basePath)[1].strip('/'),
                                                config)

            return await call_next(request)

        except Exception as e:
            if request.url.path.startswith("/admin"):
                exc_type, exc_value, exc_tb = sys.exc_info()
                WebSocketsCache.system and await WebSocketsCache.system.send_json({
                    "type": "SystemError",
                    "details": str(e),
                    "trace": traceback.format_exception(exc_type, exc_value, exc_tb)
                    })
                raise e
            raise e
