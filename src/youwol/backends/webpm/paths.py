# typing
from typing import Optional

# third parties
from aiohttp import ClientResponse
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from prometheus_client import Counter, Gauge
from pydantic import BaseModel
from starlette.responses import Response
from typing_extensions import Annotated

# Youwol backends
from youwol.backends.webpm.dependencies import (
    ConfigurationOrigin,
    CountVersions,
    Dependencies,
    dependenciesFactory,
)

router = APIRouter(tags=["webpm"])

PROXIED_HEADERS_CONTENT = [
    "content-length",
    "content-encoding",
]
PROXIED_HEADERS_CACHE = [
    "cache-control",
    "pragma",
    "expires",
    "etag",
    "last-modified",
    "age",
    "vary",
]
PROXIED_HEADERS_DEBUG = ["x-trace-id"]

PROXIED_HEADERS = [
    *PROXIED_HEADERS_CONTENT,
    *PROXIED_HEADERS_CACHE,
    *PROXIED_HEADERS_DEBUG,
]

TypedHeader = Annotated[Optional[str], Header()]

ASSET_ID = "QHlvdXdvbC9jZG4tY2xpZW50"
ASSET_PATH = "dist/@youwol/cdn-client.js"
ASSET_PATH_SOURCE_MAAP = f"{ASSET_PATH}.map"


count_version = CountVersions()
count_download = Counter("webpm_cdn_client_js", "Nb of cdn-client.js download")
count_data_transferred = Counter(
    name="webpm_data_transferred",
    documentation="Bytes transferred from upstream resources",
)
gauge_concurrent_streaming = Gauge(
    name="webpm_concurrent_streaming",
    documentation="Nb of concurrent resources streaming",
)


async def client_response_to_streaming_response(
    resp: ClientResponse,
) -> StreamingResponse:
    async def _response_generator():
        gauge_concurrent_streaming.inc()
        async for chunk, _ in resp.content.iter_chunks():
            count_data_transferred.inc(len(chunk))
            yield chunk
        resp.close()
        gauge_concurrent_streaming.dec()

    return StreamingResponse(
        content=_response_generator(),
        status_code=resp.status,
        media_type=resp.content_type,
        headers={k: v for k, v in resp.headers.items() if k.lower() in PROXIED_HEADERS},
    )


@router.post("/loading-graph")
async def loading_graph(
    request: Request, deps: Dependencies = Depends(dependenciesFactory)
) -> StreamingResponse:
    token = await deps.session_less_token_manager.get_access_token()
    return await client_response_to_streaming_response(
        await deps.client_session.post(
            f"{deps.configuration.assets_gateway_base_url}/cdn-backend/queries/loading-graph",
            json=await request.json(),
            headers={"Authorization": f"Bearer {token}"},
        ),
    )


@router.get("/resource/{rest_of_path:path}")
async def resource(
    rest_of_path: str,
    deps: Dependencies = Depends(dependenciesFactory),
) -> StreamingResponse:
    token = await deps.session_less_token_manager.get_access_token()

    return await client_response_to_streaming_response(
        await deps.client_session.get(
            f"{deps.configuration.assets_gateway_base_url}/raw/package/{rest_of_path}",
            headers={"Authorization": f"Bearer {token}"},
        ),
    )


@router.get("/cdn-client.js")
async def get_cdn_client_js_default_version(
    deps: Dependencies = Depends(dependenciesFactory),
) -> StreamingResponse:
    return await get_cdn_client_js(
        deps.configuration.default_cdn_client_version, deps=deps
    )


@router.get("/{version}/cdn-client.js")
async def get_cdn_client_js(
    version: str, deps: Dependencies = Depends(dependenciesFactory)
) -> StreamingResponse:
    count_download.inc()
    count_version.inc(version)
    resource_path = f"{ASSET_ID}/{version}/{ASSET_PATH}"
    return await resource(resource_path, deps=deps)


@router.get("/cdn-client.js.map")
async def get_cdn_client_js_map_default_version(
    deps: Dependencies = Depends(dependenciesFactory),
) -> StreamingResponse:
    return await get_cdn_client_js_map(
        deps.configuration.default_cdn_client_version, deps
    )


@router.get("/{version}/cdn-client.js.map")
async def get_cdn_client_js_map(
    version: str, deps: Dependencies = Depends(dependenciesFactory)
) -> StreamingResponse:
    resource_path = f"{ASSET_ID}/{version}/{ASSET_PATH_SOURCE_MAAP}"
    return await resource(resource_path, deps=deps)


class CdnClientConfig(BaseModel):
    id: str
    origin: ConfigurationOrigin
    pathLoadingGraph: str
    pathResource: str


@router.get("/cdn-client.config.json")
async def get_cdn_client_config_default_version(
    response: Response,
    if_none_match: TypedHeader = None,
    deps: Dependencies = Depends(dependenciesFactory),
) -> Optional[CdnClientConfig]:
    return await get_cdn_client_config(
        response,
        if_none_match=if_none_match,
        deps=deps,
    )


@router.get("/{version}/cdn-client.config.json")
async def get_cdn_client_config(
    response: Response,
    if_none_match: TypedHeader = None,
    deps: Dependencies = Depends(dependenciesFactory),
) -> Optional[CdnClientConfig]:
    etag = deps.configuration.version

    if if_none_match == str(etag):
        response.status_code = 304
        return None

    response.headers["etag"] = str(etag)
    response.headers["cache-control"] = "max-age=31536000, immutable"
    return CdnClientConfig(
        id=deps.configuration.config_id,
        origin=deps.configuration.origin,
        pathLoadingGraph="/loading-graph",
        pathResource="/resource",
    )
