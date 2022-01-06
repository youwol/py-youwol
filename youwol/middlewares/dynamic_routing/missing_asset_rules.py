
from youwol.context import Context
from .common import DispatchingRule
from .redirect import redirect_api_remote

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class GetRawDispatch(DispatchingRule):

    async def is_matching(self, request: Request, context: Context) -> bool:
        return request.method == "GET" and '/api/assets-gateway/raw/' in request.url.path

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Response:

        resp = await call_next(request)
        if resp.status_code == 404:
            headers = {"Authorization": request.headers.get("authorization")}
            resp = await redirect_api_remote(request)
            context.download_thread.enqueue_asset(url=request.url.path, context=context, headers=headers)
            return resp
        return resp


class GetMetadataDispatch(DispatchingRule):

    async def is_matching(self, request: Request, context: Context) -> bool:
        return request.method == "GET" and '/api/assets-gateway/assets/' in request.url.path

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Response:

        resp = await call_next(request)
        return await redirect_api_remote(request) if resp.status_code == 404 else resp


class PostMetadataDispatch(DispatchingRule):

    async def is_matching(self, request: Request, context: Context) -> bool:
        return request.method == "POST" and '/api/assets-gateway/assets/' in request.url.path

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Response:

        resp = await call_next(request)
        return resp
        # return await redirect_api_remote(request, context=context) if resp.status_code == 404 else resp
