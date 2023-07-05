# third parties
from fastapi import APIRouter, Depends, Query
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.assets_gateway.configurations import (
    Configuration,
    get_configuration,
)
from youwol.backends.assets_gateway.routers.common import (
    assert_read_permissions_from_raw_id,
    assert_write_permissions_folder_id,
    assert_write_permissions_from_raw_id,
    create_asset,
    delete_asset,
)
from youwol.backends.assets_gateway.utils import AssetMeta

# Youwol utilities
from youwol.utils import aiohttp_to_starlette_response
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_gateway import NewAssetResponse
from youwol.utils.http_clients.cdn_backend import (
    ListVersionsResponse,
    LoadingGraphBody,
    LoadingGraphResponseV1,
)

router = APIRouter(tags=["assets-gateway.cdn-backend"])


@router.post(
    "/publish-library", summary="upload a library", response_model=NewAssetResponse
)
async def publish_library(
    request: Request,
    folder_id: str = Query(None, alias="folder-id"),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        form = await request.form()
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        package = await configuration.cdn_client.publish(
            zip_content=await form.get("file").read(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        return await create_asset(
            request=request,
            kind="package",
            raw_id=package["id"],
            raw_response=package,
            folder_id=folder_id,
            metadata=AssetMeta(name=package["name"]),
            context=ctx,
            configuration=configuration,
        )


@router.get("/download-library/{library_id}/{version}", summary="download a library")
async def download_library(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        content = await configuration.cdn_client.download_library(
            library_id=library_id,
            version=version,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        return Response(content=content, headers={"content-type": "application/zip"})


@router.get(
    "/libraries/{library_id}",
    summary="list versions of a library",
    response_model=ListVersionsResponse,
)
async def get_library_info(
    request: Request,
    library_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.get_library_info(
            library_id=library_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/libraries/{library_id}/{version}",
    summary="return info on a specific version of a library",
)
async def get_version_info(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"library_id": library_id, "version": version}
    ) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.get_version_info(
            library_id=library_id,
            version=version,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/libraries/{library_id}", summary="delete a library")
async def delete_library(
    request: Request,
    library_id: str,
    purge: bool = False,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_write_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        resp = await configuration.cdn_client.delete_library(
            library_id=library_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        if purge:
            await delete_asset(
                raw_id=library_id, configuration=configuration, context=ctx
            )
        return resp


@router.delete("/libraries/{library_id}/{version}", summary="delete a specific version")
async def delete_version(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        await assert_write_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.delete_version(
            library_id=library_id,
            version=version,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post(
    "/queries/loading-graph",
    summary="describes the loading graph of provided libraries",
    response_model=LoadingGraphResponseV1,
)
async def resolve_loading_tree(
    request: Request,
    body: LoadingGraphBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.cdn_client.query_loading_graph(
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/resources/{library_id}/{version}", summary="get the entry point of a library"
)
async def get_entry_point(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"library_id": library_id, "version": version}
    ) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.get_entry_point(
            library_id=library_id,
            version=version,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/resources/{library_id}/{version}/{rest_of_path:path}", summary="get a resource"
)
async def get_resource(
    request: Request,
    library_id: str,
    version: str,
    rest_of_path: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request,
        with_attributes={
            "library_id": library_id,
            "version": version,
            "path": rest_of_path,
        },
    ) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.get_resource(
            library_id=library_id,
            version=version,
            rest_of_path=rest_of_path,
            reader=aiohttp_to_starlette_response,
            auto_decompress=False,
            headers=ctx.headers(),
        )


@router.get(
    "/explorer/{library_id}/{version}/{rest_of_path:path}",
    summary="return explorer data",
)
async def get_explorer(
    request: Request,
    library_id: str,
    rest_of_path: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"libraryId": library_id, version: "version"}
    ) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.get_explorer(
            library_id=library_id,
            version=version,
            folder_path=rest_of_path,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
