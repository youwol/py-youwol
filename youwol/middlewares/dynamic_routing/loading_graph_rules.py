import asyncio
import json
from typing import Optional

import aiohttp
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

import youwol.backends.cdn.root_paths as cdn
from youwol.backends.cdn.configurations import get_configuration
from youwol.backends.cdn.models import LoadingGraphBody
from youwol.environment.youwol_environment import yw_config
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol_utils import PackagesNotFound
from youwol_utils.context import Context


class GetLoadingGraphDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if '/api/assets-gateway/cdn/queries/loading-graph' not in request.url.path:
            return None

        async with context.start(action="GetLoadingGraphDispatch.apply") as ctx:

            body_raw = await request.body()

            body = LoadingGraphBody(**(json.loads(body_raw.decode('utf8'))))
            await ctx.info("Loading graph body", data=body)
            yw_conf, cdn_conf = await asyncio.gather(
                yw_config(),
                get_configuration()
                )
            try:
                resp = await cdn.resolve_loading_tree(request, body, cdn_conf)
                return JSONResponse(resp.dict())
            except PackagesNotFound:
                await ctx.info("Loading tree can not be locally resolved, proceed to remote platform")
                url = f'https://{yw_conf.selectedRemote}{request.url.path}'

                async with aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(verify_ssl=False),
                        auto_decompress=False) as session:
                    async with await session.post(url=url, json=body.dict(), headers=ctx.headers()) as resp:
                        headers_resp = {k: v for k, v in resp.headers.items()}
                        content = await resp.read()
                        return Response(status_code=resp.status, content=content, headers=headers_resp)
