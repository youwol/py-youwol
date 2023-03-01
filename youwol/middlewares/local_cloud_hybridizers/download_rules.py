from typing import Optional
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.environment import AssetDownloadThread, YouwolEnvironment
from youwol.middlewares.local_cloud_hybridizers.abstract_local_cloud_dispatch import AbstractLocalCloudDispatch
from youwol.routers.router_remote import redirect_api_remote
from youwol_utils import YouwolHeaders, decode_id
from youwol_utils.context import Context
from youwol_utils.request_info_factory import url_match


class Download(AbstractLocalCloudDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        # Caution: download should be triggered only when fetching raw data of the asset
        # not metadata (e.g. do not catch /assets-backend/assets/**).
        patterns = [
            ("custom-asset", "GET:/api/assets-gateway/assets-backend/assets/*/files/**"),
            ("story", "GET:/api/assets-gateway/stories-backend/stories/*/**"),
            ("flux-project", "GET:/api/assets-gateway/flux-backend/projects/*/**"),
            ("data", "GET:/api/assets-gateway/files-backend/files/*/**"),
            ("package", "GET:/api/assets-gateway/cdn-backend/resources/*/**"),
            # This is a deprecated end points
            ("package", "GET:/api/assets-gateway/raw/package/*/**"),
            ("flux-project", "GET:/api/assets-gateway/raw/flux-project/*/**"),
        ]
        matches = [(kind, url_match(request, pattern)) for kind, pattern in patterns]
        match = next(((kind, match[1]) for kind, match in matches if match[0]), None)
        if not match:
            return None
        kind, params = match
        raw_id = params[0][0] if len(params[0]) == 2 else params[0]
        if kind == "custom-asset":
            # In case of 'assets-gateway/assets-backend/assets/*/**', first param is actually the asset_id
            asset_id = raw_id
            raw_id = decode_id(asset_id)
        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)
        async with context.start(
                action="Download.apply",
                muted_http_errors={404}
        ) as ctx:
            download_thread = await ctx.get('download_thread', AssetDownloadThread)
            is_downloading = download_thread.is_downloading(url=request.url.path, kind=kind, raw_id=raw_id, env=env)
            # if downloading => do not try fetching the asset from local-db (the asset can be in invalid state).
            if is_downloading:
                resp = await redirect_api_remote(request, ctx)
                resp.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
                return resp

            resp = await call_next(request)
            if resp.status_code == 404:
                await ctx.info("Raw data can not be locally retrieved, proceed to remote platform")
                headers = {"Authorization": request.headers.get("authorization")}
                resp = await redirect_api_remote(request, ctx)
                resp.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
                is_downloading = download_thread.is_downloading(url=request.url.path, kind=kind, raw_id=raw_id, env=env)
                # if by the time the remote api call responded the asset is already downloading
                # => do not enqueue download
                if is_downloading:
                    return resp
                await ctx.info("~> schedule asset download")
                download_thread.enqueue_asset(url=request.url.path, kind=kind, raw_id=raw_id, context=ctx,
                                              headers=headers)
                return resp
            resp.headers[YouwolHeaders.youwol_origin] = request.url.hostname
            return resp
