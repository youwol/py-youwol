import asyncio
import json

import aiohttp
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import youwol.services.backs.cdn.root_paths as cdn
from context import Context
from .common import DispatchingRule
from youwol.services.backs.cdn.configurations import get_configuration
from youwol.configuration.youwol_configuration import yw_config
from services.backs.cdn.models import LoadingGraphBody
from youwol_utils import PackagesNotFound


class GetLoadingGraphDispatch(DispatchingRule):

    async def is_matching(self, request: Request, context: Context) -> bool:
        return '/api/assets-gateway/cdn/queries/loading-graph' in request.url.path

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Response:

        body_raw = await request.body()

        body = LoadingGraphBody(**(json.loads(body_raw.decode('utf8'))))
        yw_conf, cdn_conf = await asyncio.gather(
            yw_config(),
            get_configuration()
            )
        try:
            resp = await cdn.resolve_loading_tree(request, body, cdn_conf)
            return JSONResponse(resp.dict())
        except PackagesNotFound:
            url = f'https://{yw_conf.selectedRemote}{request.url.path}'
            headers = {"Authorization": request.headers.get("authorization")}
            async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(verify_ssl=False),
                    auto_decompress=False) as session:
                async with await session.post(url=url, json=body.dict(), headers=headers) as resp:
                    headers_resp = {k: v for k, v in resp.headers.items()}
                    content = await resp.read()
                    return Response(status_code=resp.status, content=content, headers=headers_resp)
