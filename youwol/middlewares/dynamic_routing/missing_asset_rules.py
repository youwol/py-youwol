from typing import Optional

from fastapi import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.environment.auto_download_thread import AssetDownloadThread
from youwol.environment.clients import LocalClients
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.utils.utils_low_level import redirect_api_remote
from youwol_utils.context import Context


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

        if not (request.method == "POST" and '/api/assets-gateway/assets/' in request.url.path):
            return None

        env = await context.get('env', YouwolEnvironment)
        asset_id = request.url.path.split('/api/assets-gateway/assets/')[1].split('/')[0]

        try:
            # 'assets' and not 'assets_gateway' client is used such that following request won't be intercepted by
            # dynamic_routing middlewares.
            _resp = await LocalClients.get_assets_client(env).get(asset_id=asset_id)
            # If the asset is in local: we only update the local version
            return await call_next(request)
        except HTTPException as e:
            if e.status_code != 404:
                raise e

        resp_remote = await redirect_api_remote(request)

        if resp_remote.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="The asset seems to not exist neither in remote or local envs."
            )
        if resp_remote.status_code != 200:
            raise HTTPException(
                status_code=resp_remote.status_code,
                detail="An error occurred while fetching the asset in remote env."
            )
        return resp_remote
