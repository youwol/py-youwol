"""
This file gathers the hybrid local/cloud middlewares regarding custom backends components.
"""

# third parties
from fastapi import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.routers.environment import AssetsDownloader

# Youwol utilities
from youwol.utils import Context, encode_id
from youwol.utils.request_info_factory import url_match

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch
from .common import package_latest_info


class DownloadBackend(AbstractLocalCloudDispatch):
    """
    Handles automatic download of backends in the local CDN if not found locally at the relevant version.
    If the resource is found locally, it proceeds to the target destination.
    If the resource is not found locally:
    *  it adds and waits a download task for the corresponding asset.
    *  it proceeds to the target destination.

    """

    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Response | None:
        """
        This dispatch match the endpoints:
         *  `*:/backends/**`

        It returns `None` otherwise.

        Parameters:
            incoming_request: The incoming request.
            call_next: The next endpoint in the chain.
            context: The current context.

        Return:
            Eventually download the backend if not included in the local components at the relevant version,
            then proceed to the target destination and return the response.
        """
        [match, resolved] = url_match(incoming_request, "*:/backends/**")

        if not match:
            return None
        params = resolved[1]
        kind = "package"
        package_name = params[0]
        raw_id = encode_id(package_name)
        semver = params[1]

        async with context.start(action="DownloadBackend.apply") as ctx:
            download_info = await package_latest_info(
                package_name=package_name, semver=semver, context=ctx
            )

            if not download_info.download_needed:
                return await call_next(incoming_request)

            assets_downloader = await ctx.get("assets_downloader", AssetsDownloader)

            await ctx.info("~> wait for asset download")
            status = await assets_downloader.wait_asset(
                url=incoming_request.url.path, kind=kind, raw_id=raw_id, context=ctx
            )
            if not status.succeeded:
                raise HTTPException(
                    status_code=500,
                    detail="The backend failed to download, refer to the application"
                    " `@youwol/co-lab` for more insights.",
                )
            return await call_next(incoming_request)
