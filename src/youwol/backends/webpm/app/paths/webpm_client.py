# typing
from typing import Optional

# third parties
from fastapi import Depends
from fastapi.responses import StreamingResponse
from starlette.responses import Response

# relative
from ..constantes import (
    WEBPM_CLIENT_ASSET_ID,
    WEBPM_CLIENT_ASSET_PATH,
    WEBPM_CLIENT_ASSET_PATH_SOURCE_MAP,
)
from ..dependencies import Dependencies, dependenciesFactory
from ..metrics import count_download, count_version
from .common import TypedHeader, get_client_config
from .models import ClientConfig
from .root import resource, router


@router.get("/webpm-client.js")
async def get_webpm_client_js_default_version(
    deps: Dependencies = Depends(dependenciesFactory),
) -> StreamingResponse:
    return await get_webpm_client_js(
        deps.configuration.default_webpm_client_version, deps=deps
    )


@router.get("/{version}/webpm-client.js")
async def get_webpm_client_js(
    version: str, deps: Dependencies = Depends(dependenciesFactory)
) -> StreamingResponse:
    count_download.inc()
    count_version.inc(version)
    resource_path = f"{WEBPM_CLIENT_ASSET_ID}/{version}/{WEBPM_CLIENT_ASSET_PATH}"
    return await resource(resource_path, deps=deps)


@router.get("/webpm-client.js.map")
async def get_webpm_client_js_map_default_version(
    deps: Dependencies = Depends(dependenciesFactory),
) -> StreamingResponse:
    return await get_webpm_client_js_map(
        deps.configuration.default_webpm_client_version, deps
    )


@router.get("/{version}/webpm-client.js.map")
async def get_webpm_client_js_map(
    version: str, deps: Dependencies = Depends(dependenciesFactory)
) -> StreamingResponse:
    resource_path = (
        f"{WEBPM_CLIENT_ASSET_ID}/{version}/{WEBPM_CLIENT_ASSET_PATH_SOURCE_MAP}"
    )
    return await resource(resource_path, deps=deps)


@router.get("/webpm-client.config.json")
async def get_webpm_client_config_default_version(
    response: Response,
    if_none_match: Optional[TypedHeader] = None,
    deps: Dependencies = Depends(dependenciesFactory),
) -> Optional[ClientConfig]:
    return get_client_config(
        response,
        if_none_match=if_none_match,
        deps=deps,
    )


@router.get("/{version}/webpm-client.config.json")
async def get_webpm_client_config(
    response: Response,
    if_none_match: Optional[TypedHeader] = None,
    deps: Dependencies = Depends(dependenciesFactory),
) -> Optional[ClientConfig]:
    return get_client_config(
        response,
        if_none_match=if_none_match,
        deps=deps,
    )
