# typing
from typing import Optional

# third parties
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.router_remote import redirect_api_remote

# Youwol utilities
from youwol.utils import YouwolHeaders
from youwol.utils.context import Context
from youwol.utils.request_info_factory import url_match

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch


class ForwardOnly(AbstractLocalCloudDispatch):
    async def apply(
        self, request: Request, call_next: RequestResponseEndpoint, context: Context
    ) -> Optional[Response]:
        patterns = [
            "GET:/api/assets-gateway/assets/**",
            "GET:/api/assets-gateway/cdn-backend/libraries/**",
            "GET:/api/assets-gateway/assets-backend/assets/**",
            "GET:/api/assets-gateway/treedb-backend/items/**",
        ]
        matches = [url_match(request, pattern) for pattern in patterns]
        match = next((match for match in matches if match[0]), None)
        if not match:
            return None

        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        async with context.start(
            action="ForwardOnlyDispatch.apply", muted_http_errors={404}
        ) as ctx:
            resp = await call_next(request)
            if resp.status_code == 404:
                await ctx.info(
                    "Forward request to remote as it can not proceed locally "
                )
                resp = await redirect_api_remote(request=request, context=ctx)
                resp.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
                return resp

            resp.headers[YouwolHeaders.youwol_origin] = request.url.hostname
            return resp