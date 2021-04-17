from typing import List, cast, Union

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.context import Context
from youwol.errors import HTTPResponseException
from youwol.routers.api import redirect_get_api, redirect_post_api, redirect_put_api, redirect_delete_api
from youwol.routers.backends.utils import get_all_backends
from youwol.web_socket import WebSocketsCache


async def redirect_api_local(request: Request, base_path: str, config: YouwolConfiguration):
    service_name = base_path.split('/api/')[1]
    rest_of_path = request.url.path.split(f'/{service_name}/')[1]
    if request.method == 'GET':
        return await redirect_get_api(request, service_name, rest_of_path, config)
    if request.method == 'POST':
        return await redirect_post_api(request, service_name, rest_of_path, config)
    if request.method == 'PUT':
        return await redirect_put_api(request, service_name, rest_of_path, config)
    if request.method == 'DELETE':
        return await redirect_delete_api(request, service_name, rest_of_path, config)
    pass


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
        if service_name == "flux-backend":
            print("toto")
        backend = next(backend for backend in backends if backend.info.name == service_name)

        if await is_backend_alive(request, backend.info.name, backend.pipeline.serve.health, config):
            return config
        return None
    except (StopIteration, AttributeError):
        return None


class NativesBypassMiddleware(BaseHTTPMiddleware):

    def __init__(self,
                 app: ASGIApp,
                 api_bypass_base_paths: List[str]
                 ) -> None:
        super().__init__(app)
        self.api_bypass_base_paths = api_bypass_base_paths

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

        api_base_path = next((skipped for skipped in self.api_bypass_base_paths
                              if request.url.path.startswith(skipped)),
                             None)

        config = await is_running(request=request, api_base_path=api_base_path, context=context)
        if config:
            return await redirect_api_local(request, api_base_path, config)

        resp = await call_next(request)
        # the cache is disabled for assets (especially for packages)
        if "assets-gateway/raw/package" in str(request.url) and "-next" in str(request.url) and request.method == "GET":
            resp.headers.update({'cache-control': 'no-store'})

        return resp
