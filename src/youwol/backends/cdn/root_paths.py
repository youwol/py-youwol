# standard library
import asyncio
import io
import json

# typing
from typing import Any

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
from youwol.utils import PackagesNotFound
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
from youwol.utils.types import AnyDict

router = APIRouter(tags=["cdn-backend"])


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-backend ok"}


@router.post(
    "/publish-library",
    summary="Publish a library from a zip file.",
    response_model=PublishResponse,
)
async def publish_library(
    request: Request,
    file: UploadFile = File(...),
    content_encoding: str = Form("identity"),
    configuration: Configuration = Depends(get_configuration),
) -> PublishResponse:
    """
    Publishes a library from a zip file:
        *  Publish the files in the storage
        *  Publish a document in the no-sql table
        *  Publish files in the storage (under folder `/auto-generated/explorer`) to summarize the files' organization.

    Requirements:
        *  a `package.json` file is available in the zip, its location define the **reference path**.
        Only the files in this folder and below are published.
        *  `package.json` is a valid JSON file, including the fields:
           *  'name' : the package name, also UID.
           *  'version' : the package version, need to follow [semantic versioning](https://semver.org/).
           Pre-releases allowed are defined [here](@yw-nav-class:youwol.backends.cdn.configurations.Constants).
           *  'main' : the path of the main entry point, with respect to the **reference path**.

    Parameters:
        request: Incoming request.
        file: Zip file including the packaged files.
        content_encoding: Deprecated, use the default value.
        configuration: Injected configuration of the service.

    Return:
        Publication summary.
    """

    async with Context.start_ep(request=request, with_labels=["Publish"]) as ctx:
        return await publish_package(
            file=file.file,
            filename=file.filename if file.filename else "uploaded_file",
            content_encoding=content_encoding,
            configuration=configuration,
            context=ctx,
        )


@router.get("/download-library/{library_id}/{version}", summary="Download a library.")
async def download_library(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
) -> Response:
    """
    Downloads a library as zip file.

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name
        version: explicit version (no semver allowed)
        configuration: Injected configuration of the service.

    Return:
        Response
    """
    async with Context.start_ep(request=request, with_labels=["Download"]) as ctx:
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
    summary="Query library information.",
    response_model=ListVersionsResponse,
)
async def get_library_info(
    request: Request,
    library_id: str,
    semver: str = QueryParam(None),
    max_count: int = QueryParam(1000, alias="max-count"),
    configuration: Configuration = Depends(get_configuration),
) -> ListVersionsResponse:
    """
    Queries library information.

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        semver: Semantic versioning query.
        max_count: Maximum count of versions returned.
        configuration: Injected configuration of the service.

    Return:
        Response
    """
    async with Context.start_ep(request=request) as ctx:
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
) -> Library:
    async with context.start(
        action="get_version_info_impl",
        with_attributes={"library_id": library_id, "version": version},
    ) as ctx:
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
            raise e


@router.get(
    "/libraries/{library_id}/{version}",
    summary="Query specific version information of a library.",
    response_model=Library,
)
async def get_version_info(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
) -> Library:
    """
    Queries specific version information of a library.

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        version: Explicit version.
        configuration: Injected configuration of the service.

    Return:
        Response
    """
    async with Context.start_ep(
        request=request, with_attributes={"library_id": library_id, "version": version}
    ) as ctx:
        return await get_version_info_impl(
            library_id=library_id,
            version=version,
            configuration=configuration,
            context=ctx,
        )


@router.delete(
    "/libraries/{library_id}",
    summary="Delete a library.",
    response_model=DeleteLibraryResponse,
)
async def delete_library(
    request: Request,
    library_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> DeleteLibraryResponse:
    """
    Deletes a library (all versions).

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        configuration: Injected configuration of the service.

    Return:
        Response
    """
    async with Context.start_ep(
        request=request, with_attributes={"libraryId": library_id}
    ) as ctx:
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


@router.delete(
    "/libraries/{library_id}/{version}", summary="Delete specific version of a library."
)
async def delete_version(
    request: Request,
    library_id: str,
    version: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Deletes specific version of a library.

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        version: Explicit version.
        configuration: Injected configuration of the service.

    Return:
        A dictionary with attribute `deletedCount`.
    """
    async with Context.start_ep(
        request=request, with_attributes={"library_id": library_id, "version": version}
    ) as ctx:
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
    summary="Resolves the loading graph of provided libraries.",
    response_model=LoadingGraphResponseV1,
)
async def resolve_loading_tree(
    request: Request,
    body: LoadingGraphBody,
    configuration: Configuration = Depends(get_configuration),
) -> LoadingGraphResponseV1:
    """
    Resolves the loading graph of provided libraries.

    Parameters:
        request: Incoming request.
        body: requested libraries.
        configuration: Injected configuration of the service.

    Return:
        The loading graph.
    """

    versions_cache: dict[LibName, list[str]] = {}
    full_data_cache: dict[ExportedKey, LibraryResolved] = {}
    resolutions_cache: dict[QueryKey, ResolvedQuery] = {}

    def to_libraries_resolved(input_elements: list[dict[str, Any]]):
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
                namespace=(
                    element["library_name"].split("/")[0]
                    if "/" in element["library_name"]
                    else element["library_name"]
                ),
                type="library",
            )
            for element in input_elements
        ]

    async with Context.start_ep(request=request, body=body) as ctx:
        await ctx.info(text="Start resolving loading graph", data=body)
        empty: list[str] = []
        extra_index = (
            await decode_extra_index(body.extraIndex, ctx)
            if body.extraIndex
            else list(empty)
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
            get_full_exported_symbol(d.name, d.version): (
                to_package_id(d.name),
                get_url(d),
            )
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
) -> Response:
    """
    Fetches the entry point of a library..

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        version: semantic versioning request.
        configuration: Injected configuration of the service.

    Return:
        Response
    """

    async with Context.start_ep(
        action="fetch entry point",
        request=request,
        with_attributes={"library_id": library_id, "version": version},
    ) as ctx:
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
) -> Response:
    """
    Fetches a file from a library.

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        version: semantic versioning request.
        rest_of_path: Path of the file within the library.
        configuration: Injected configuration of the service.

    Return:
        Response
    """
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
) -> ExplorerResponse:
    """
    Describes the files content structure of the root folder of a library.

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        version: semantic versioning request.
        configuration: Injected configuration of the service.

    Return:
        Response
    """

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
) -> ExplorerResponse:
    """
    Describes the files content structure of library's folder.

    Parameters:
        request: Incoming request.
        library_id: Base64 encoded library name.
        version: semantic versioning request.
        rest_of_path: path of the folder (referenced from the root folder of the library).
        configuration: Injected configuration of the service.

    Return:
        Response
    """

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
        items_json = json.load(io.BytesIO(items))
        return ExplorerResponse(**items_json)
