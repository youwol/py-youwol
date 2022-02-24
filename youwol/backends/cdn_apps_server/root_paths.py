import base64
from typing import List

import aiohttp
from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils import raise_exception_from_response
from youwol_utils.context import Context
from .configurations import get_configuration

router = APIRouter()
# For the applications below the href path must be fixed by appending /dist at the end
to_fix = [
    "@youwol/platform",
    "@youwol/flux-builder",
    "@youwol/flux-runner",
    "@youwol/explorer",
    "@youwol/stories",
    "@youwol/exhibition-halls"
]


def get_info(segments: List[str]):
    namespace = segments[0]
    name = segments[1]
    full_name = f"{namespace}/{name}" if namespace else name
    version = segments[2]
    default = 'index.html' if full_name in to_fix else ''
    resource = '/'.join(segments[3:]) if len(segments) >= 4 else default
    return namespace, name, version, resource


async def get_raw_resource(
        namespace: str,
        name: str,
        version: str,
        resource: str,
        ctx: Context):
    full_name = f"{namespace}/{name}" if namespace else name
    raw_id = base64.urlsafe_b64encode(str.encode(full_name)).decode()
    config = await get_configuration()
    url = f"{config.gtw_client.url_base}/raw/package/{raw_id}/{version}/{resource}"

    if full_name in to_fix:
        url = f"{config.gtw_client.url_base}/raw/package/{raw_id}/{version}/dist/{resource}"

    cors_headers = {
        'cross-origin-opener-policy': 'same-origin',
        'cross-origin-embedder-policy': 'require-corp'
    }

    async with aiohttp.ClientSession(auto_decompress=False) as session:
        async with await session.get(url=url, headers=ctx.headers()) as resp:
            if resp.status == 200:
                return Response(
                    content=await resp.read(),
                    headers={
                        **{k: v for k, v in resp.headers.items()},
                        **cors_headers
                    }
                )
            await raise_exception_from_response(resp)


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-apps-server ok"}


@router.get("/{rest_of_path:path}")
async def catch_all_no_namespace(
        request: Request,
        rest_of_path: str
):
    async with Context.start_ep(
            action="fetch application",
            request=request
    ) as ctx:
        segments = rest_of_path.strip('/').split('/')
        namespace, name, version, resource = get_info(segments) \
            if segments[0].startswith('@') \
            else get_info([""] + segments)
        return await get_raw_resource(namespace, name, version, resource, ctx)
