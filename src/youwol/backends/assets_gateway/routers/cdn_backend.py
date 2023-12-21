# third parties
from fastapi import APIRouter, Depends, Query
from starlette.datastructures import UploadFile
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
    """
    If access is granted, forwarded to
    [cdn.publish_library](@yw-nav-func:youwol.backends.cdn.root_paths.publish_library)
    endpoint of [cdn](@yw-nav-mod:youwol.backends.cdn) service.

    On top of uploading the package, it:
        *  create an asset using the [assets](@yw-nav-mod:youwol.backends.assets) service.
        *  create an explorer item using [tree_db](@yw-nav-mod:youwol.backends.tree_db) service.

    Parameters:
        request: Incoming request.
        folder_id: Folder ID (from files explorer) in which the asset is located in the file explorer.
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.assets_gateway.configurations.Configuration).
    """
    async with Context.start_ep(request=request) as ctx:
        form = await request.form()
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise ValueError("Field `file` of form is not of type `UploadFile`")
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        package = await configuration.cdn_client.publish(
            zip_content=await file.read(),
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
    """
    If permissions are granted, forward to
    [cdn.download_library](@yw-nav-func:youwol.backends.cdn.root_paths.download_library)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
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
    summary="""
Retrieve info of a library, including available versions sorted from the most recent to the oldest.
library_id:  id of the library
query parameters:
   semver: semantic versioning query
   max_count: maximum count of versions returned
    """,
    response_model=ListVersionsResponse,
)
async def get_library_info(
    request: Request,
    library_id: str,
    semver: str = Query(None),
    max_count: int = Query(None, alias="max-count"),
    configuration: Configuration = Depends(get_configuration),
):
    """
    If permissions are granted, forward to
    [cdn.get_library_info](@yw-nav-func:youwol.backends.cdn.root_paths.get_library_info)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
    async with Context.start_ep(request=request) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.get_library_info(
            library_id=library_id,
            semver=semver,
            max_count=max_count,
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
    """
    If permissions are granted, forward to
    [cdn.get_version_info](@yw-nav-func:youwol.backends.cdn.root_paths.get_version_info)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
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
    """
    If permissions are granted, forward to
    [cdn.delete_library](@yw-nav-func:youwol.backends.cdn.root_paths.delete_library)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
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
    """
    If permissions are granted, forward to
    [cdn.delete_version](@yw-nav-func:youwol.backends.cdn.root_paths.delete_version)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
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
    """
    Forward to
    [cdn.query_loading_graph](@yw-nav-func:youwol.backends.cdn.root_paths.query_loading_graph)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
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
    """
    If permissions are granted, forward to
    [cdn.get_entry_point](@yw-nav-func:youwol.backends.cdn.root_paths.get_entry_point)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
    async with Context.start_ep(
        request=request, with_attributes={"library_id": library_id, "version": version}
    ) as ctx:
        await assert_read_permissions_from_raw_id(
            raw_id=library_id, configuration=configuration, context=ctx
        )
        return await configuration.cdn_client.get_entry_point(
            library_id=library_id,
            version=version,
            custom_reader=aiohttp_to_starlette_response,
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
    """
    If permissions are granted, forward to
    [cdn.get_resource](@yw-nav-func:youwol.backends.cdn.root_paths.get_resource)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
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
            custom_reader=aiohttp_to_starlette_response,
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
    """
    If permissions are granted, forward to
    [cdn.get_explorer](@yw-nav-func:youwol.backends.cdn.root_paths.get_explorer)
    of [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """
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
