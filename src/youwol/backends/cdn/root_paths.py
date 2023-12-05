# standard library
import asyncio
import io
import json

# typing
from typing import Dict, List, Optional

# third parties
from fastapi import APIRouter, Depends, File, Form, HTTPException
from fastapi import Query as QueryParam
from fastapi import UploadFile
from semantic_version import NpmSpec, Version
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.cdn.configurations import (
    Configuration,
    Constants,
    get_configuration,
)
from youwol.backends.cdn.loading_graph_implementation import (
    ExportedKey,
    LibName,
    QueryKey,
    ResolvedQuery,
    get_api_key,
    get_full_exported_symbol,
    loading_graph,
    resolve_dependencies_recursive,
)
from youwol.backends.cdn.utils import (
    fetch_resource,
    get_path,
    get_url,
    library_model_from_doc,
    list_versions,
    publish_package,
    resolve_explicit_version,
    resolve_resource,
    to_package_id,
    to_package_name,
)
from youwol.backends.cdn.utils_indexing import get_version_number_str

# Youwol utilities
from youwol.utils import JSON, PackagesNotFound
from youwol.utils.clients.docdb.models import Query, QueryBody, WhereClause
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import (
    DeleteLibraryResponse,
    ExplorerResponse,
    Library,
    LibraryQuery,
    LibraryResolved,
    ListVersionsResponse,
    LoadingGraphBody,
    LoadingGraphResponseV1,
    PublishResponse,
    get_exported_symbol,
)
from youwol.utils.http_clients.cdn_backend.utils import decode_extra_index

router = APIRouter(tags=["cdn-backend"])


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-backend ok"}


@router.post(
    "/publish-library", summary="upload a library", response_model=PublishResponse
)
async def publish_library(
    request: Request,
    file: UploadFile = File(...),
    content_encoding: str = Form("identity"),
    configuration: Configuration = Depends(get_configuration),
):
    # https://www.toptal.com/python/beginners-guide-to-concurrency-and-parallelism-in-python
    # Publish needs to be done using a queue to let the cdn pods fully available to fetch resources

    async with Context.start_ep(
        request=request, with_labels=["Publish"]
    ) as ctx:  # type: Context
        return await publish_package(
            file.file, file.filename, content_encoding, configuration, ctx
        )


@router.get("/download-library/{library_id}/{version}", summary="download a library")
async def download_library(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_labels=["Download"]
    ) as ctx:  # type: Context
        version = await resolve_explicit_version(
            package_name=to_package_name(library_id),
            input_version=version,
            configuration=configuration,
            context=ctx,
        )

        file_system = configuration.file_system
        path = get_path(
            library_id=library_id, version=version, rest_of_path="__original.zip"
        )
        await ctx.info("Original zip path retrieved", data={"path": path})
        content = await file_system.get_object(object_id=path, headers=ctx.headers())
        return Response(content, media_type="multipart/form-data")


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
    semver: str = QueryParam(None),
    max_count: int = QueryParam(1000, alias="max-count"),
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[ListVersionsResponse] = None
    async with Context.start_ep(
        request=request, response=lambda: response
    ) as ctx:  # type: Context
        name = to_package_name(library_id)
        # If a semver is requested we basically fetch all versions and proceed with filtering afterward using NpmSpec.
        # It would be interesting to proceed with the versions filtering directly from the CQL query to scylla-db.
        # This optimization remains to be done.
        response = await list_versions(
            name=name,
            context=ctx,
            max_results=1000 if semver else max_count,
            configuration=configuration,
        )
        if semver is None:
            return response
        if len(response.versions) == 1000:
            raise HTTPException(
                status_code=500,
                detail=f"cdn.get_library_info => library {name} has more than 1000 "
                f"versions.",
            )
        releases_by_version = {r.version: r for r in response.releases}
        selector = NpmSpec(semver)
        versions = [v for v in response.versions if selector.match(Version(v))]
        versions = versions[0:max_count]
        return ListVersionsResponse(
            **{
                **response.dict(),
                "versions": versions,
                "releases": [releases_by_version[v] for v in versions],
            }
        )


async def get_version_info_impl(
    library_id: str, version: str, configuration: Configuration, context: Context
):
    async with context.start(
        action="get_version_info_impl",
        with_attributes={"library_id": library_id, "version": version},
    ) as ctx:  # type: Context
        library_name = to_package_name(library_id)
        _, resolved_version, _ = await resolve_resource(
            library_id=library_id,
            input_version=version,
            configuration=configuration,
            context=ctx,
        )
        doc_db = configuration.doc_db

        try:
            d = await doc_db.get_document(
                partition_keys={"library_name": library_name},
                clustering_keys={
                    "version_number": get_version_number_str(resolved_version)
                },
                owner=Constants.owner,
                headers=ctx.headers(),
            )
            return library_model_from_doc(d)
        except HTTPException as e:
            if e.status_code == 404:
                raise PackagesNotFound(
                    context="Failed to retrieve a package",
                    packages=[f"{library_name}#{resolved_version}"],
                )


@router.get(
    "/libraries/{library_id}/{version}",
    summary="return info on a specific version of a library",
    response_model=Library,
)
async def get_version_info(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"library_id": library_id, "version": version}
    ) as ctx:  # type: Context
        return await get_version_info_impl(
            library_id=library_id,
            version=version,
            configuration=configuration,
            context=ctx,
        )


@router.delete(
    "/libraries/{library_id}",
    summary="delete a library",
    response_model=DeleteLibraryResponse,
)
async def delete_library(
    request: Request,
    library_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"libraryId": library_id}
    ) as ctx:  # type: Context
        doc_db = configuration.doc_db
        name = to_package_name(library_id)
        query = QueryBody(
            max_results=100,
            query=Query(
                where_clause=[
                    WhereClause(column="library_name", relation="eq", term=name)
                ]
            ),
        )
        await ctx.info("scylla-db query", data=query)
        resp_query = await doc_db.query(
            query_body=query, owner=Constants.owner, headers=ctx.headers()
        )

        await asyncio.gather(
            *[
                doc_db.delete_document(
                    doc=d, owner=Constants.owner, headers=ctx.headers()
                )
                for d in resp_query["documents"]
            ]
        )
        return DeleteLibraryResponse(deletedVersionsCount=len(resp_query["documents"]))


@router.delete("/libraries/{library_id}/{version}", summary="delete a specific version")
async def delete_version(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"library_id": library_id, "version": version}
    ) as ctx:  # type: Context
        doc_db = configuration.doc_db
        file_system = configuration.file_system
        library_name = to_package_name(library_id)

        doc = await doc_db.get_document(
            partition_keys={"library_name": library_name},
            clustering_keys={"version_number": get_version_number_str(version)},
            owner=Constants.owner,
            headers=ctx.headers(),
        )
        await doc_db.delete_document(
            doc=doc, owner=Constants.owner, headers=ctx.headers()
        )

        path_folder = f"{library_name}/{version}"

        await asyncio.gather(
            file_system.remove_folder(
                prefix=f"libraries/{path_folder}",
                raise_not_found=False,
                headers=ctx.headers(),
            ),
            file_system.remove_folder(
                prefix=f"generated/explorer/{path_folder}",
                raise_not_found=False,
                headers=ctx.headers(),
            ),
        )
        return {"deletedCount": 1}


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
    versions_cache: Dict[LibName, List[str]] = {}
    full_data_cache: Dict[ExportedKey, LibraryResolved] = {}
    resolutions_cache: Dict[QueryKey, ResolvedQuery] = {}

    def to_libraries_resolved(input_elements: List[JSON]):
        return [
            LibraryResolved(
                name=element["library_name"],
                aliases=element["aliases"],
                dependencies=[
                    LibraryQuery(name=e.split("#")[0], version=e.split("#")[1])
                    for e in element["dependencies"]
                ],
                bundle=element["bundle"],
                exportedSymbol=get_exported_symbol(element["library_name"]),
                apiKey=get_api_key(element["version"]),
                version=element["version"],
                id=to_package_id(element["library_name"]),
                fingerprint=element["fingerprint"],
                namespace=element["library_name"].split("/")[0]
                if "/" in element["library_name"]
                else element["library_name"],
                type="library",
            )
            for element in input_elements
        ]

    async with Context.start_ep(request=request, body=body) as ctx:  # type: Context
        await ctx.info(text="Start resolving loading graph", data=body)
        extra_index = (
            await decode_extra_index(body.extraIndex, ctx) if body.extraIndex else []
        )
        root_name = "!!root!!"
        # This is for backward compatibility when single lib version download were assumed
        dependencies = (
            [
                LibraryQuery(name=name, version=version)
                for name, version in body.libraries.items()
            ]
            if isinstance(body.libraries, dict)
            else body.libraries
        )

        resolved_libraries = await resolve_dependencies_recursive(
            from_libraries=[
                LibraryResolved(
                    namespace="",
                    id="",
                    type="",
                    exportedSymbol=root_name,
                    aliases=[root_name],
                    apiKey=get_api_key("1.0.0-does-not-matter"),
                    fingerprint="",
                    bundle="",
                    name=root_name,
                    version="1.0.0-does-not-matter",
                    dependencies=dependencies,
                )
            ],
            using=body.using,
            extra_index=to_libraries_resolved(extra_index),
            versions_cache=versions_cache,
            resolutions_cache=resolutions_cache,
            full_data_cache=full_data_cache,
            configuration=configuration,
            context=ctx,
        )

        resolved_libraries = [
            lib for lib in resolved_libraries if lib.name != root_name
        ]
        items_dict = {
            get_full_exported_symbol(d.name, d.version): [
                to_package_id(d.name),
                get_url(d),
            ]
            for d in resolved_libraries
        }

        graph = await loading_graph(
            remaining=resolved_libraries,
            items_dict=items_dict,
            resolutions_dict=resolutions_cache,
            context=ctx,
        )

        response = LoadingGraphResponseV1(
            graphType="sequential-v2",
            lock=[Library(**lib.dict()) for lib in resolved_libraries],
            definition=graph,
        )
        await ctx.info("Loading graph resolved", data=response)
        return response


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
        action="fetch entry point",
        request=request,
        with_attributes={"library_id": library_id, "version": version},
    ) as ctx:  # type: Context
        package_name, version, max_age = await resolve_resource(
            library_id=library_id,
            input_version=version,
            configuration=configuration,
            context=ctx,
        )
        doc = await configuration.doc_db.get_document(
            partition_keys={"library_name": package_name},
            clustering_keys={"version_number": get_version_number_str(version)},
            owner=Constants.owner,
            headers=ctx.headers(),
        )

        path = get_path(
            library_id=library_id, version=version, rest_of_path=doc["bundle"]
        )
        await ctx.info(f"Fetch script at path {path}")
        return await fetch_resource(
            request=request,
            path=path,
            max_age=max_age,
            configuration=configuration,
            context=ctx,
        )


@router.get(
    "/resources/{library_id}/{version}/{rest_of_path:path}", summary="get a library"
)
async def get_resource(
    request: Request,
    library_id: str,
    version: str,
    rest_of_path: str,
    configuration: Configuration = Depends(get_configuration),
):
    if not rest_of_path:
        return await get_entry_point(
            request=request,
            library_id=library_id,
            version=version,
            configuration=configuration,
        )
    async with Context.start_ep(
        action="fetch resource",
        request=request,
        with_attributes={"rest_of_path": rest_of_path},
    ) as ctx:  # type: Context
        await ctx.info(f"Target resource: '{rest_of_path}'")
        _, version, max_age = await resolve_resource(
            library_id=library_id,
            input_version=version,
            configuration=configuration,
            context=ctx,
        )

        path = get_path(
            library_id=library_id, version=version, rest_of_path=rest_of_path
        )
        await ctx.info("forward path constructed", data={"path": path})
        return await fetch_resource(
            request=request,
            path=path,
            max_age=max_age,
            configuration=configuration,
            context=ctx,
        )


@router.get(
    "/explorer/{library_id}/{version}",
    summary="get a library",
    response_model=ExplorerResponse,
)
async def explorer_root(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
):
    return await explorer(
        request=request,
        library_id=library_id,
        version=version,
        rest_of_path="",
        configuration=configuration,
    )


@router.get(
    "/explorer/{library_id}/{version}/{rest_of_path:path}",
    summary="get a library",
    response_model=ExplorerResponse,
)
async def explorer(
    request: Request,
    library_id: str,
    version: str,
    rest_of_path: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        action="get explorer's items",
        request=request,
        with_attributes={"rest_of_path": rest_of_path},
    ) as ctx:  # type: Context
        try:
            package_name = to_package_name(library_id)
        except Exception:
            raise HTTPException(
                status_code=400, detail=f"'{library_id}' is not a valid library id"
            )

        path = f"generated/explorer/{package_name.replace('@', '')}/{version}/{rest_of_path}/".replace(
            "//", "/"
        )
        file_system = configuration.file_system
        try:
            items = await file_system.get_object(
                object_id=path + "items.json", headers=ctx.headers()
            )
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            return ExplorerResponse()
        items = json.load(io.BytesIO(items))
        return ExplorerResponse(**items)
