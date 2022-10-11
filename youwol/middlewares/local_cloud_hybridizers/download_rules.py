from typing import Optional
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.environment.auto_download_thread import AssetDownloadThread
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.utils.utils_low_level import redirect_api_remote
from youwol_utils.context import Context
from youwol_utils.request_info_factory import url_match


class Download(AbstractDispatch):

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
                action="Download.apply",
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
