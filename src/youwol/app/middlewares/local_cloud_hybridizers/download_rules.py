# typing
from typing import Optional

# third parties
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.environment.download_assets.auto_download_thread import (
    AssetDownloadThread,
)
from youwol.app.routers.router_remote import redirect_api_remote

# Youwol utilities
from youwol.utils import YouwolHeaders, decode_id
from youwol.utils.context import Context
from youwol.utils.request_info_factory import url_match

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch


class Download(AbstractLocalCloudDispatch):
    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
        # Caution: download should be triggered only when fetching raw data of the asset
        # not metadata (e.g. do not catch /assets-backend/assets/**).
        patterns = [
            (
                "custom-asset",
                "GET:/api/assets-gateway/assets-backend/assets/*/files/**",
            ),
            ("story", "GET:/api/assets-gateway/stories-backend/stories/*/**"),
            ("flux-project", "GET:/api/assets-gateway/flux-backend/projects/*/**"),
            ("data", "GET:/api/assets-gateway/files-backend/files/*/**"),
            ("package", "GET:/api/assets-gateway/cdn-backend/resources/*/**"),
            # This is a deprecated end points
            ("package", "GET:/api/assets-gateway/raw/package/*/**"),
            ("flux-project", "GET:/api/assets-gateway/raw/flux-project/*/**"),
        ]
        matches = [
            (kind, url_match(incoming_request, pattern)) for kind, pattern in patterns
        ]
        match = next(((kind, match[1]) for kind, match in matches if match[0]), None)
        if not match:
            return None
        kind, params = match
        raw_id = params[0][0] if len(params[0]) == 2 else params[0]
        if kind == "custom-asset":
            # In case of 'assets-gateway/assets-backend/assets/*/**', first param is actually the asset_id
            asset_id = raw_id
            raw_id = decode_id(asset_id)
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        async with context.start(
            action="Download.apply", muted_http_errors={404}
        ) as ctx:
            download_thread = await ctx.get("download_thread", AssetDownloadThread)
            is_downloading = download_thread.is_downloading(
                url=incoming_request.url.path, kind=kind, raw_id=raw_id, env=env
            )
            # if downloading => do not try fetching the asset from local-db (the asset can be in invalid state).
            if is_downloading:
                resp = await redirect_api_remote(incoming_request, ctx)
                resp.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
                return resp

            resp = await call_next(incoming_request)
            if resp.status_code == 404:
                await ctx.info(
                    "Raw data can not be locally retrieved, proceed to remote platform"
                )
                headers = {
                    "Authorization": incoming_request.headers.get("authorization")
                }
                resp = await redirect_api_remote(incoming_request, ctx)
                resp.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
                is_downloading = download_thread.is_downloading(
                    url=incoming_request.url.path, kind=kind, raw_id=raw_id, env=env
                )
                # if by the time the remote api call responded the asset is already downloading
                # => do not enqueue download
                if is_downloading:
                    return resp
                await ctx.info("~> schedule asset download")
                download_thread.enqueue_asset(
                    url=incoming_request.url.path,
                    kind=kind,
                    raw_id=raw_id,
                    context=ctx,
                    headers=headers,
                )
                return resp
            resp.headers[YouwolHeaders.youwol_origin] = incoming_request.url.hostname
            return resp
