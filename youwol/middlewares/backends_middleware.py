import itertools
import traceback
from typing import Union
import sys

from fastapi import HTTPException

from middlewares.redirect import redirect_api_remote, redirect_api_local
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.context import Context
from youwol.errors import HTTPResponseException
from youwol.routers.api import redirect_get_api
from youwol.routers.backends.utils import get_all_backends
from youwol.web_socket import WebSocketsCache

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


async def is_backend_alive(request: Request, service_name: str, health_url: str, config: YouwolConfiguration) -> bool:

    try:
        resp = await redirect_get_api(request, service_name, health_url[1:], config)
        if resp.status_code == 200:
            return True
    except HTTPException:
        return False


async def is_running(request: Request, api_base_path: str, context: Context) -> Union[None, YouwolConfiguration]:

    config = await yw_config()
    try:
        backends = await get_all_backends(context)
        service_name = api_base_path.split('api/')[1]

        backend = next(backend for backend in backends if backend.info.name == service_name)

        if await is_backend_alive(request, backend.info.name, backend.pipeline.serve.health, config):
            return config
        return None
    except (StopIteration, AttributeError):
        return None


class BackendsMiddleware(BaseHTTPMiddleware):

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

        config_backends = itertools.chain.from_iterable([t for t in config.userConfig.backends.targets.values()])
        api_base_paths = [t.basePath for t in config_backends if t.basePath]
        api_base_path = next((base_path for base_path in api_base_paths
                              if request.url.path.startswith(base_path)),
                             None)

        config = await is_running(request=request, api_base_path=api_base_path, context=context)

        try:
            if config:
                return await redirect_api_local(request, api_base_path, config)

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
