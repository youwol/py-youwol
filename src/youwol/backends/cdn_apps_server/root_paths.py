# standard library
import base64

# typing
from typing import List

# third parties
import aiohttp

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.cdn_apps_server.configurations import get_configuration

# Youwol utilities
from youwol.utils import raise_exception_from_response
from youwol.utils.context import Context

router = APIRouter(tags=["cdn-apps-server"])


def get_info(segments: List[str]):
    namespace = segments[0]
    name = segments[1]
    version = segments[2]
    resource = "/".join(segments[3:]) if len(segments) >= 4 else ""
    return namespace, name, version, resource


async def get_raw_resource(
    namespace: str, name: str, version: str, resource: str, ctx: Context
):
    full_name = f"{namespace}/{name}" if namespace else name
    raw_id = base64.urlsafe_b64encode(str.encode(full_name)).decode()
    config = await get_configuration()
    url = (
        f"{config.assets_gtw_client.url_base}/raw/package/{raw_id}/{version}/{resource}"
    )

    cors_headers = {
        "cross-origin-opener-policy": "same-origin",
        "cross-origin-embedder-policy": "require-corp",
    }

    async with aiohttp.ClientSession(auto_decompress=False) as session:
        async with await session.get(url=url, headers=ctx.headers()) as resp:
            if resp.status < 400:
                return Response(
                    content=await resp.read(),
                    headers={**dict(resp.headers.items()), **cors_headers},
                )
            await raise_exception_from_response(resp)


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-apps-server ok"}


@router.get("/{rest_of_path:path}")
async def catch_all_no_namespace(request: Request, rest_of_path: str):
    async with Context.start_ep(action="fetch application", request=request) as ctx:
        segments = rest_of_path.strip("/").split("/")
        namespace, name, version, resource = (
            get_info(segments)
            if segments[0].startswith("@")
            else get_info([""] + segments)
        )
        return await get_raw_resource(namespace, name, version, resource, ctx)
