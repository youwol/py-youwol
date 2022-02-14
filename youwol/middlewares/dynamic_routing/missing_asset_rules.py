import json
from typing import Optional, cast, Any

from fastapi import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from youwol.environment.auto_download_thread import AssetDownloadThread
from youwol.environment.clients import LocalClients
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.routers.commons import ensure_local_path
from youwol.utils.utils_low_level import redirect_api_remote
from youwol_utils.context import Context
from youwol_utils.request_info_factory import url_match


class GetRawDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:
        if not (request.method == "GET" and '/api/assets-gateway/raw/' in request.url.path):
            return None

        async with context.start(action="GetRawDispatch.apply") as ctx:
            resp = await call_next(request)
            if resp.status_code == 404:
                await ctx.info("Raw data can not be locally retrieved, proceed to remote platform")
                headers = {"Authorization": request.headers.get("authorization")}
                resp = await redirect_api_remote(request, ctx)
                thread = await ctx.get('download_thread', AssetDownloadThread)

                async with ctx.start(action="Enqueue asset for download in local store") as ctx_1:
                    thread.enqueue_asset(url=request.url.path, context=ctx_1, headers=headers)
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

        async with context.start(action="GetMetadataDispatch.apply") as ctx:
            resp = await call_next(request)
            if resp.status_code == 404:
                await ctx.info("Metadata can not be locally retrieved, proceed to remote platform")
                return await redirect_api_remote(request=request, context=ctx)

            return resp


class PostMetadataDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not (request.method == "POST" and '/api/assets-gateway/assets/' in request.url.path):
            return None

        async with context.start(action="PostMetadataDispatch.apply") as ctx:
            env = await ctx.get('env', YouwolEnvironment)
            asset_id = request.url.path.split('/api/assets-gateway/assets/')[1].split('/')[0]

            try:
                # 'assets' and not 'assets_gateway' client is used such that following request won't be intercepted by
                # dynamic_routing middlewares.
                await LocalClients.get_assets_client(env).get(asset_id=asset_id, headers=ctx.headers())
                await ctx.info('Asset found in local store, only this version is updated')
                return await call_next(request)
            except HTTPException as e:
                if e.status_code != 404:
                    raise e

            await ctx.info('Asset not found in local store, proceed to remote platform')
            resp_remote = await redirect_api_remote(request=request, context=ctx)

            if resp_remote.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="The asset seems to exist neither in remote nor local envs."
                )
            if resp_remote.status_code != 200:
                raise HTTPException(
                    status_code=resp_remote.status_code,
                    detail="An error occurred while fetching the asset in remote env."
                )
            return resp_remote


class CreateAssetDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        match, replaced = url_match(request=request, pattern='PUT:/api/assets-gateway/assets/*/location/*')
        if not match:
            return None
        env = await context.get('env', YouwolEnvironment)

        async with context.start(action="CreateAssetDispatch.apply") as ctx:
            folder_id = replaced[-1]
            await ensure_local_path(folder_id=folder_id, env=env, context=ctx)
            resp = await call_next(request)
            binary = b''
            async for data in cast(Any, resp).body_iterator:
                binary += data
            data = {
                **json.loads(binary),
                **{
                    'origin': {
                        'remote': False,
                        'local': True
                    }
                }
            }
            return JSONResponse(data)
