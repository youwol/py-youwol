# typing
from typing import Optional

# third parties
from fastapi.params import Depends
from starlette.responses import Response, StreamingResponse

# relative
from ..constantes import ASSET_ID, ASSET_PATH, ASSET_PATH_SOURCE_MAAP
from ..dependencies import Dependencies, dependenciesFactory
from ..metrics import count_download, count_version
from .common import TypedHeader, get_client_config
from .models import ClientConfig
from .root import resource, router


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


@router.get("/cdn-client.config.json")
async def get_cdn_client_config_default_version(
    response: Response,
    if_none_match: TypedHeader = None,
    deps: Dependencies = Depends(dependenciesFactory),
) -> Optional[ClientConfig]:
    return get_client_config(
        response=response,
        if_none_match=if_none_match,
        deps=deps,
    )


@router.get("/{version}/cdn-client.config.json")
async def get_cdn_client_config(
    response: Response,
    if_none_match: TypedHeader = None,
    deps: Dependencies = Depends(dependenciesFactory),
) -> Optional[ClientConfig]:
    return get_client_config(response=response, if_none_match=if_none_match, deps=deps)
