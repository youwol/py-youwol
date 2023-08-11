# typing
from typing import Awaitable, Dict, Union

# third parties
import aiohttp

from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.assets_gateway.configurations import (
    Configuration,
    get_configuration,
)
from youwol.backends.assets_gateway.routers.common import (
    assert_read_permissions_from_raw_id,
)

# Youwol utilities
from youwol.utils import (
    JSON,
    aiohttp_to_starlette_response,
    raise_exception_from_response,
)
from youwol.utils.context import Context

router = APIRouter(tags=["assets-gateway.deprecated"])


@router.get(
    "/raw/package/{raw_id}/{rest_of_path:path}",
    summary="get raw cdn-package. DEPRECATED",
)
async def get_raw_package(
    request: Request,
    rest_of_path: str,
    raw_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    ⚠️ Deprecated, use :func:`youwol.backends.assets_gateway.routers.cdn_backend.get_resource`.

    This end point is deprecated, it is used in following circumstances (only related to cdn):
        - in @youwol/cdn-client/client.ts: the url constructed to fetch cdn files use:
         `/api/assets-gateway/raw/package/${cdn_url}`
         => it needs to be updated by `/api/assets-gateway/cdn-backend/resources/${cdn_url}`
         - in saved flux project and stories the above URL are 'pined' in a sort of '.lock' files
         => these project need to be updated after the first point is solved
    """
    async with Context.start_ep(
        request=request, with_attributes={"raw_id": raw_id, "path": rest_of_path}
    ) as ctx:
        version = rest_of_path.split("/")[0]
        rest_of_path = "/".join(rest_of_path.split("/")[1:])
        await assert_read_permissions_from_raw_id(
            raw_id=raw_id, configuration=configuration, context=ctx
        )

        return await configuration.cdn_client.get_resource(
            library_id=raw_id,
            version=version,
            rest_of_path=rest_of_path,
            reader=aiohttp_to_starlette_response,
            auto_decompress=False,
            headers=ctx.headers(),
        )


# Following deprecated end points are used in flux-projects including modules providing access
# to the files in the YouWol environment (like 'Drive', 'FilePicker', etc).
# The libraries are '@youwol/flux-youwol-essentials' & '@youwol/youwol-essentials'.


async def forward_deprecated_get(
    request, forward_path, configuration: Configuration, to_json=True
) -> Union[Awaitable[JSON], Union[Awaitable[bytes], Dict[str, str]]]:
    async with Context.start_ep(request=request) as ctx:
        url = f"{request.base_url}api/{forward_path}"
        if configuration.https:
            url = url.replace("http://", "https://")
        await ctx.info(f"Deprecated GET end-point => redirect to GET:{url}")
        headers = ctx.headers()
        async with aiohttp.ClientSession() as session:
            async with await session.get(url=url, headers=headers) as resp:
                if resp.status == 200:
                    return (
                        await resp.json()
                        if to_json
                        else (await resp.read(), resp.headers)
                    )
                await raise_exception_from_response(resp)


@router.get("/raw/data/{raw_id}", summary="get raw data. DEPRECATED")
async def get_raw_data(
    request: Request,
    raw_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    content, headers = await forward_deprecated_get(
        request=request,
        to_json=False,
        forward_path=f"assets-gateway/files-backend/files/{raw_id}",
        configuration=configuration,
    )
    return Response(content=content, headers=headers)


@router.get("/groups", summary="get user's groups. DEPRECATED")
async def groups(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    resp = await forward_deprecated_get(
        request=request, forward_path="accounts/session", configuration=configuration
    )
    return resp["userInfo"]


@router.get("/tree/groups/{group_id}/drives", summary="get drives. DEPRECATED")
async def drives(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    return await forward_deprecated_get(
        request=request,
        forward_path=f"assets-gateway/treedb-backend/groups/{group_id}/drives",
        configuration=configuration,
    )


@router.get("/tree/items/{item_id}", summary="get item. DEPRECATED")
async def item(
    request: Request,
    item_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    return await forward_deprecated_get(
        request=request,
        forward_path=f"assets-gateway/treedb-backend/items/{item_id}",
        configuration=configuration,
    )
