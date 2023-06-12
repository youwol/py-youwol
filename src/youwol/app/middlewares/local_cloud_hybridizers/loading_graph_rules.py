# standard library
import json

# typing
from typing import Optional

# third parties
import aiohttp

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Youwol application
from youwol.app.environment import YouwolEnvironment

# Youwol backends
from youwol.backends.cdn import Dependencies, resolve_loading_tree

# Youwol utilities
from youwol.utils import DependenciesError, YouwolHeaders
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import LoadingGraphBody, patch_loading_graph

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch


class GetLoadingGraph(AbstractLocalCloudDispatch):
    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
        if (
            "/api/assets-gateway/cdn-backend/queries/loading-graph"
            not in incoming_request.url.path
        ):
            return None

        async with context.start(
            action="GetLoadingGraphDispatch.apply", muted_http_errors={404}
        ) as ctx:
            body_raw = await incoming_request.body()

            body = LoadingGraphBody(**(json.loads(body_raw.decode("utf8"))))
            await ctx.info("Loading graph body", data=body)
            cdn_conf = await Dependencies.get_configuration()

            env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
            try:
                resp = await resolve_loading_tree(incoming_request, body, cdn_conf)
                return JSONResponse(
                    resp.dict(),
                    headers={
                        YouwolHeaders.youwol_origin: incoming_request.url.hostname
                    },
                )
            except DependenciesError as e:
                await ctx.warning(
                    text="Loading tree can not be resolved locally, proceed to remote platform",
                    data=e.detail,
                )
                url = f"https://{env.get_remote_info().host}{incoming_request.url.path}"

                async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(verify_ssl=False),
                    auto_decompress=False,
                ) as session:
                    async with await session.post(
                        url=url, json=body.dict(), headers=ctx.headers()
                    ) as resp:
                        headers_resp = dict(resp.headers.items())
                        headers_resp[
                            YouwolHeaders.youwol_origin
                        ] = env.get_remote_info().host
                        content = await resp.read()
                        if not resp.ok:
                            await ctx.error(
                                text="Loading tree has not been resolved in remote neither"
                            )
                            return Response(
                                status_code=resp.status,
                                content=content,
                                headers=headers_resp,
                            )
                        #  This is a patch to keep until new version of cdn-backend is deployed
                        graph = json.loads(content)
                        if graph["graphType"] != "sequential-v2":
                            patch_loading_graph(graph)
                        patched_content = json.dumps(graph)
                        headers_resp["Content-Length"] = f"{len(patched_content)}"
                        return Response(
                            status_code=resp.status,
                            content=patched_content,
                            headers=headers_resp,
                        )
