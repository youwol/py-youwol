# standard library
import json

# typing
from typing import Any, Optional, cast

# third parties
from fastapi import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.commons import ensure_local_path
from youwol.app.routers.router_remote import redirect_api_remote

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.request_info_factory import url_match

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch


class PostMetadataDeprecated(AbstractLocalCloudDispatch):
    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
        match, replaced = url_match(
            request=incoming_request, pattern="POST:/api/assets-gateway/assets/*"
        )
        if not match:
            return None

        async with context.start(action="PostMetadataDispatch.apply") as ctx:
            env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
            asset_id = replaced[0]

            try:
                # 'assets' and not 'assets_gateway' client is used such that following request won't be intercepted by
                # dynamic_routing middlewares.
                await LocalClients.get_assets_client(env).get(
                    asset_id=asset_id, headers=ctx.headers()
                )
                await ctx.info(
                    "Asset found in local store, only this version is updated"
                )
                return await call_next(incoming_request)
            except HTTPException as e:
                if e.status_code != 404:
                    raise e

            await ctx.info("Asset not found in local store, proceed to remote platform")
            resp_remote = await redirect_api_remote(
                request=incoming_request, context=ctx
            )

            if resp_remote.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="The asset seems to exist neither in remote nor local envs.",
                )
            if resp_remote.status_code != 200:
                raise HTTPException(
                    status_code=resp_remote.status_code,
                    detail="An error occurred while fetching the asset in remote env.",
                )
            return resp_remote


class CreateAssetDeprecated(AbstractLocalCloudDispatch):
    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
        match, replaced = url_match(
            request=incoming_request,
            pattern="PUT:/api/assets-gateway/assets/*/location/*",
        )
        if not match:
            return None
        env = await context.get("env", YouwolEnvironment)

        async with context.start(action="CreateAssetDispatchDeprecated.apply") as ctx:
            folder_id = replaced[-1]
            await ensure_local_path(folder_id=folder_id, env=env, context=ctx)
            resp = await call_next(incoming_request)
            binary = b""
            async for data in cast(Any, resp).body_iterator:
                binary += data
            data = {
                **json.loads(binary),
                **{"origin": {"remote": False, "local": True}},
            }
            return JSONResponse(status_code=resp.status_code, content=data)
