from youwol.middlewares.models_dispatch import AbstractDispatch

from youwol.utils.utils_low_level import redirect_api_remote
from youwol_utils.request_info_factory import url_match
from youwol_utils.context import Context
from typing import Optional
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class ForwardOnly(AbstractDispatch):

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
        match = next((match for match in matches if match[0]), None)
        if not match:
            return None

        async with context.start(action="ForwardOnlyDispatch.apply", muted_http_errors={404}) as ctx:
            resp = await call_next(request)
            if resp.status_code == 404:
                await ctx.info("Forward request to remote as it can not proceed locally ")
                return await redirect_api_remote(request=request, context=ctx)

            return resp