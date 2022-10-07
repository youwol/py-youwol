import asyncio
import json
from typing import Optional

import aiohttp
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from youwol.environment.youwol_environment import yw_config
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol_cdn_backend import resolve_loading_tree, Dependencies
from youwol_utils import DependenciesError
from youwol_utils.context import Context
from youwol_utils.http_clients.cdn_backend import LoadingGraphBody, patch_loading_graph


class GetLoadingGraphDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if '/api/assets-gateway/cdn-backend/queries/loading-graph' not in request.url.path:
            return None

        async with context.start(action="GetLoadingGraphDispatch.apply", muted_http_errors={404}) as ctx:

            body_raw = await request.body()

            body = LoadingGraphBody(**(json.loads(body_raw.decode('utf8'))))
            await ctx.info("Loading graph body", data=body)
            yw_conf, cdn_conf = await asyncio.gather(
                yw_config(),
                Dependencies.get_configuration()
                )
            try:
                resp = await resolve_loading_tree(request, body, cdn_conf)
                return JSONResponse(resp.dict())
            except DependenciesError as e:
                await ctx.warning(
                    text="Loading tree can not be resolved locally, proceed to remote platform",
                    data=e.detail
                )
                url = f'https://{yw_conf.selectedRemote}{request.url.path}'

                async with aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(verify_ssl=False),
                        auto_decompress=False) as session:
                    async with await session.post(url=url, json=body.dict(), headers=ctx.headers()) as resp:
                        headers_resp = {k: v for k, v in resp.headers.items()}
                        content = await resp.read()
                        if not resp.ok:
                            await ctx.error(text="Loading tree has not been resolved in remote neither")
                            return Response(status_code=resp.status, content=content, headers=headers_resp)
                        #  This is a patch to keep until new version of cdn-backend is deployed
                        graph = json.loads(content)
                        if graph['graphType'] != 'sequential-v2':
                            patch_loading_graph(graph)
                        patched_content = json.dumps(graph)
                        headers_resp['Content-Length'] = f"{len(patched_content)}"
                        return Response(status_code=resp.status, content=patched_content, headers=headers_resp)
