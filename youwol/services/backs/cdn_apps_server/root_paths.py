from typing import List, Mapping
import base64

import aiohttp
from starlette.requests import Request
from starlette.responses import Response
from fastapi import APIRouter
from youwol_utils import generate_headers_downstream, log_info
from .configurations import get_configuration
from youwol_utils import raise_exception_from_response

router = APIRouter()


def get_info(segments: List[str]):
    namespace = segments[0]
    name = segments[1]
    version = segments[2]
    resource = '/'.join(segments[3:]) if len(segments) >= 4 else 'index.html'
    return namespace, name, version, resource


async def get_raw_resource(
        namespace: str,
        name: str,
        version: str,
        resource: str,
        headers: Mapping[str, str]):

    full_name = f"{namespace}/{name}" if namespace else name
    raw_id = base64.urlsafe_b64encode(str.encode(full_name)).decode()
    config = await get_configuration()
    url = f"{config.gtw_client.url_base}/raw/package/{raw_id}/{version}/dist/{resource}"

    cors_headers = {
        'cross-origin-opener-policy': 'same-origin',
        'cross-origin-embedder-policy': 'require-corp'
        }

    async with aiohttp.ClientSession(auto_decompress=False) as session:
        async with await session.get(url=url, headers=headers) as resp:
            if resp.status == 200:
                return Response(
                    content=await resp.read(),
                    headers={
                        **{k: v for k, v in resp.headers.items()},
                        **(cors_headers if resource == "index.html" else {})
                        }
                    )
            await raise_exception_from_response(resp)


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-apps-server ok"}


@router.get("/{rest_of_path:path}")
async def catch_all_no_namespace(
        request: Request,
        rest_of_path
        ):
    headers = generate_headers_downstream(request.headers)
    segments = rest_of_path.split('/')
    namespace, name, version, resource = get_info(segments) \
        if segments[0].startswith('@') \
        else get_info([""] + segments)
    log_info("forward request to CDN:", namespace=namespace, name=name, version=version, resource=resource)
    return await get_raw_resource(namespace, name, version, resource, headers)
