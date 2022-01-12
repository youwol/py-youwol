from typing import Optional

from youwol_utils.context import Context
from youwol.environment.auto_download_thread import AssetDownloadThread
from youwol.utils_low_level import redirect_api_remote

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.middlewares.models_dispatch import AbstractDispatch


class GetRawDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:
        if not (request.method == "GET" and '/api/assets-gateway/raw/' in request.url.path):
            return None
        resp = await call_next(request)
        if resp.status_code == 404:
            headers = {"Authorization": request.headers.get("authorization")}
            resp = await redirect_api_remote(request)
            thread = await context.get('download_thread', AssetDownloadThread)
            thread.enqueue_asset(url=request.url.path, context=context, headers=headers)
            return resp
        return resp


class GetMetadataDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not (request.method == "GET" and '/api/assets-gateway/assets/' in request.url.path):
            return None
        resp = await call_next(request)
        return await redirect_api_remote(request) if resp.status_code == 404 else resp


class PostMetadataDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not(request.method == "POST" and '/api/assets-gateway/assets/' in request.url.path):
            return None

        resp = await call_next(request)
        # One other option would be to sync remote asset metadata:
        # return await redirect_api_remote(request, context=context) if resp.status_code == 404 else resp
        return resp
