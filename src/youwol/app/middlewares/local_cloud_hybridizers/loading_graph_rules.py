# standard library
import itertools
import json

from timeit import default_timer as timer

# typing
from typing import Optional

# third parties
import aiohttp

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import YouwolEnvironment

# Youwol utilities
from youwol.utils import LocalDocDbClient, YouwolHeaders
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import (
    LoadingGraphBody,
    get_api_key,
    patch_loading_graph,
)
from youwol.utils.http_clients.cdn_backend.utils import encode_extra_index

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch


async def get_extra_index(context: Context) -> Optional[str]:
    """
    Useful items are the libraries from the local cdn database from which we keep only the latest version w/ all API
    version.
    """
    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
    docdb: LocalDocDbClient = env.backends_configuration.cdn_backend.doc_db
    async with context.start(action="get_extra_index", muted_http_errors={404}) as ctx:

        def get_key(d):
            return d["library_name"] + "@" + get_api_key(d["version"])

        useful_items = []
        sorted_api_key = sorted(docdb.data["documents"], key=get_key)
        for _, g in itertools.groupby(sorted_api_key, key=get_key):
            sorted_version_number = sorted(
                list(g), key=lambda d: int(d["version_number"])
            )
            useful_items.append(sorted_version_number[-1])
        if not useful_items:
            await ctx.info(text="No useful items retrieved")
            return None

        await ctx.info(
            text="Useful items retrieved",
            data={d["library_id"]: d for d in useful_items},
        )
        encoded = await encode_extra_index(useful_items, context=ctx)
        return encoded


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
            body = LoadingGraphBody(**(json.loads(body_raw.decode("utf-8"))))
            await ctx.info("Loading graph body", data=body)
            env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
            extra_index = await get_extra_index(ctx)
            url = f"https://{env.get_remote_info().host}{incoming_request.url.path}"
            await ctx.info(
                text="Send loading graph query to remote", data={"urlRemote": url}
            )
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(verify_ssl=False),
                auto_decompress=False,
            ) as session:
                body = LoadingGraphBody(
                    libraries=body.libraries, using=body.using, extraIndex=extra_index
                )
                start = timer()
                async with await session.post(
                    url=url, json=body.dict(), headers=ctx.headers()
                ) as resp:
                    end = timer()
                    await ctx.info(
                        f"Response received from remote in {int(1000 * (end - start))} ms"
                    )
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
