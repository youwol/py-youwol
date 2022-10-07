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

        patterns = [
            ("story", "GET:/api/assets-gateway/stories-backend/stories/*"),
            ("flux-project", "GET:/api/assets-gateway/flux-backend/projects/*"),
            ("data", "GET:/api/assets-gateway/files-backend/files/*"),
            ("package", "GET:/api/assets-gateway/cdn-backend/resources/*/**"),
            # This is a deprecated end point
            ("package", "GET:/api/assets-gateway/raw/package/*/**"),
        ]
        matches = [(kind, url_match(request, pattern)) for kind, pattern in patterns]
        match = next(((kind, match[1]) for kind, match in matches if match[0]), None)
        if not match:
            return None
        kind, params = match
        raw_id = params[0]

        async with context.start(
                action="GetRawDispatch.apply",
                muted_http_errors={404}
        ) as ctx:
            resp = await call_next(request)
            if resp.status_code == 404:
                await ctx.info("Raw data can not be locally retrieved, proceed to remote platform")
                headers = {"Authorization": request.headers.get("authorization")}
                resp = await redirect_api_remote(request, ctx)
                thread = await ctx.get('download_thread', AssetDownloadThread)
                await ctx.info("~> schedule asset download")
                thread.enqueue_asset(url=request.url.path, kind=kind, raw_id=raw_id, context=ctx, headers=headers)
                return resp
            return resp


class ForwardOnlyDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        patterns = [
            'GET:/api/assets-gateway/assets/**',
            'GET:/api/assets-gateway/cdn-backend/libraries/**',
            'GET:/api/assets-gateway/assets-backend/assets/**'
        ]
        matches = [url_match(request, pattern) for pattern in patterns]
        match = next((match for match in matches if match), None)
        if not match:
            return None

        async with context.start(action="ForwardOnlyDispatch.apply", muted_http_errors={404}) as ctx:
            resp = await call_next(request)
            if resp.status_code == 404:
                await ctx.info("Forward request to remote as it can not proceed locally ")
                return await redirect_api_remote(request=request, context=ctx)

            return resp


class PostMetadataDispatchDeprecated(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        match, replaced = url_match(request=request, pattern='POST:/api/assets-gateway/assets/*')
        if not match:
            return None

        async with context.start(action="PostMetadataDispatch.apply") as ctx:
            env = await ctx.get('env', YouwolEnvironment)
            asset_id = replaced[0]

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


class CreateAssetDispatchDeprecated(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        match, replaced = url_match(request=request, pattern='PUT:/api/assets-gateway/assets/*/location/*')
        if not match:
            return None
        env = await context.get('env', YouwolEnvironment)

        async with context.start(action="CreateAssetDispatchDeprecated.apply") as ctx:
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
            return JSONResponse(status_code=resp.status_code, content=data)
