from aiohttp import ClientConnectorError

from .common import DispatchingRule
from .redirect import redirect_api_local, redirect_get
from youwol.context import Context
from youwol.routers.backends.utils import get_all_backends, BackEnd

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


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

"""
if request.url.path.startswith('/remote/api'):
    return await redirect_api_remote(
        request=request,
        redirect_url=f"https://{config.selectedRemote}{request.url.path.split('/remote')[1]}")
"""


class LiveServingBackendDispatch(DispatchingRule):

    backend: BackEnd = None

    async def is_matching(self, request: Request, context: Context) -> bool:

        backends = await get_all_backends(context)
        self.backend = next((backend for backend in backends
                             if backend.target.basePath and request.url.path.startswith(backend.target.basePath)),
                            None)
        if not self.backend:
            return False

        return await is_local_backend_alive(request=request, backend=self.backend)

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Response:
        return await redirect_api_local(request,
                                        self.backend.info.name,
                                        request.url.path.split(self.backend.target.basePath)[1].strip('/'),
                                        context.config)
