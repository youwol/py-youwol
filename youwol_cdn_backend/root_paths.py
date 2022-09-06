import asyncio
import io
import json
import shutil
from typing import Optional, Dict, List

from fastapi import UploadFile, File, HTTPException, Form, APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

from youwol_cdn_backend.loading_graph_implementation import resolve_dependencies_recursive, loading_graph, \
    get_full_exported_symbol, ResolvedQuery, LibName, ExportedKey, QueryKey, get_api_key, get_exported_symbol

from youwol_utils import PackagesNotFound
from youwol_utils.clients.docdb.models import WhereClause, QueryBody, Query
from youwol_utils.context import Context
from youwol_utils.http_clients.cdn_backend import (
    PublishResponse, ListVersionsResponse, PublishLibrariesResponse,
    LoadingGraphResponseV1, LoadingGraphBody, Library,
    ExplorerResponse, DeleteLibraryResponse, LibraryQuery, LibraryResolved
)
from youwol_cdn_backend.configurations import Configuration, Constants, get_configuration
from youwol_cdn_backend.resources_initialization import synchronize
from youwol_cdn_backend.utils import (
    extract_zip_file, to_package_id, create_tmp_folder,
    to_package_name, get_url, publish_package,
    list_versions,
    fetch_resource, resolve_resource, get_path, resolve_explicit_version
)

from youwol_cdn_backend.utils_indexing import get_version_number_str

router = APIRouter(tags=["cdn-backend"])


@router.get("/healthz")
async def healthz():
    return {
        "status": "cdn-backend ok"
    }


@router.post("/publish-library",
             summary="upload a library",
             response_model=PublishResponse)
async def publish_library(
        request: Request,
        file: UploadFile = File(...),
        content_encoding: str = Form('identity'),
        configuration: Configuration = Depends(get_configuration)):
    # https://www.toptal.com/python/beginners-guide-to-concurrency-and-parallelism-in-python
    # Publish needs to be done using a queue to let the cdn pods fully available to fetch resources

    async with Context.start_ep(
            request=request,
            with_labels=['Publish']
    ) as ctx:  # type: Context
        return await publish_package(file.file, file.filename, content_encoding, configuration, ctx)


@router.get("/download-library/{library_id}/{version}",
            summary="download a library"
            )
async def download_library(
        request: Request,
        library_id: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request,
            with_labels=['Download']
    ) as ctx:  # type: Context
        version = await resolve_explicit_version(package_name=to_package_name(library_id), input_version=version,
                                                 configuration=configuration, context=ctx)

        file_system = configuration.file_system
        path = get_path(library_id=library_id, version=version, rest_of_path='__original.zip')
        await ctx.info("Original zip path retrieved", data={"path": path})
        content = await file_system.get_object(object_name=path, headers=ctx.headers())
        return Response(content, media_type='multipart/form-data')


@router.post("/publish-libraries",
             summary="sync the cdn resources from the content of the given .zip file",
             response_model=PublishLibrariesResponse)
async def publish_libraries(
        request: Request,
        file: UploadFile = File(...),
        configuration: Configuration = Depends(get_configuration)
):
    response: Optional[PublishLibrariesResponse] = None

    async with Context.start_ep(
            request=request,
            response=lambda: response
    ) as ctx:  # type: Context

        dir_path, zip_path, zip_dir_name = create_tmp_folder(file.filename)

        try:
            compressed_size = extract_zip_file(file.file, zip_path, dir_path)
            files_count, libraries_count, namespaces = await synchronize(dir_path, zip_dir_name, configuration,
                                                                         ctx.headers(), context=ctx)

            response = PublishLibrariesResponse(
                filesCount=files_count,
                librariesCount=libraries_count,
                compressedSize=compressed_size,
                namespaces=namespaces
            )
            return response
        finally:
            shutil.rmtree(dir_path)


@router.get("/libraries/{library_id}", summary="list versions of a library",
            response_model=ListVersionsResponse)
async def get_library_info(
        request: Request,
        library_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    response: Optional[ListVersionsResponse] = None
    async with Context.start_ep(
            request=request,
            response=lambda: response
    ) as ctx:  # type: Context
        name = to_package_name(library_id)
        response = await list_versions(name=name, context=ctx, max_results=1000, configuration=configuration)
        return response


@router.get(
    "/libraries/{library_id}/{version}",
    summary="return info on a specific version of a library",
    response_model=Library
)
async def get_version_info(
        request: Request,
        library_id: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request,
            with_attributes={"library_id": library_id, "version": version}
    ) as ctx:  # type: Context
        library_name = to_package_name(library_id)
        if version == 'latest':
            versions_resp = await list_versions(name=library_name, max_results=1, context=ctx,
                                                configuration=configuration)
            version = versions_resp.versions[0]

        doc_db = configuration.doc_db

        try:
            d = await doc_db.get_document(
                partition_keys={"library_name": library_name},
                clustering_keys={"version_number": get_version_number_str(version)},
                owner=Constants.owner,
                headers=ctx.headers())
            return Library(name=d["library_name"], version=d["version"], namespace=d["namespace"],
                           id=to_package_id(d["library_name"]), type=d["type"], fingerprint=d["fingerprint"],
                           exportedSymbol=get_exported_symbol(d["library_name"]),
                           apiKey=get_api_key(d['version'])
                           )
        except HTTPException as e:
            if e.status_code == 404:
                raise PackagesNotFound(
                    context="Failed to retrieve a package",
                    packages=[f"{library_name}#{version}"]
                )


@router.delete(
    "/libraries/{library_id}",
    summary="delete a library",
    response_model=DeleteLibraryResponse
)
async def delete_library(
        request: Request,
        library_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request,
            with_attributes={"libraryId": library_id}
    ) as ctx:  # type: Context

        doc_db = configuration.doc_db
        name = to_package_name(library_id)
        query = QueryBody(
            max_results=100,
            query=Query(where_clause=[WhereClause(column="library_name", relation="eq", term=name)])
        )
        await ctx.info("scylla-db query", data=query)
        resp_query = await doc_db.query(query_body=query, owner=Constants.owner, headers=ctx.headers())

        await asyncio.gather(*[doc_db.delete_document(doc=d, owner=Constants.owner, headers=ctx.headers())
                               for d in resp_query["documents"]])
        return DeleteLibraryResponse(deletedVersionsCount=len(resp_query["documents"]))


@router.delete("/libraries/{library_id}/{version}", summary="delete a specific version")
async def delete_version(
        request: Request,
        library_id: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)
):

    async with Context.start_ep(
            request=request,
            with_attributes={"library_id": library_id, "version": version}
    ) as ctx:  # type: Context

        doc_db = configuration.doc_db
        file_system = configuration.file_system
        library_name = to_package_name(library_id)

        doc = await doc_db.get_document(
            partition_keys={"library_name": library_name},
            clustering_keys={"version_number": get_version_number_str(version)},
            owner=Constants.owner,
            headers=ctx.headers())
        await doc_db.delete_document(doc=doc, owner=Constants.owner, headers=ctx.headers())

        path_folder = f"{library_name}/{version}"

        await asyncio.gather(
            file_system.remove_folder(prefix=f"libraries/{path_folder}", raise_not_found=False, headers=ctx.headers()),
            file_system.remove_folder(prefix=f"generated/explorer/{path_folder}", raise_not_found=False,
                                      headers=ctx.headers())
        )
        return {"deletedCount": 1}


@router.post("/queries/loading-graph",
             summary="describes the loading graph of provided libraries",
             response_model=LoadingGraphResponseV1)
async def resolve_loading_tree(
        request: Request,
        body: LoadingGraphBody,
        configuration: Configuration = Depends(get_configuration)
):
    versions_cache: Dict[LibName, List[str]] = {}
    full_data_cache: Dict[ExportedKey, LibraryResolved] = {}
    resolutions_cache:  Dict[QueryKey, ResolvedQuery] = {}
    async with Context.start_ep(
            request=request,
            body=body
    ) as ctx:  # type: Context

        await ctx.info(text=f"Start resolving loading graph", data=body)
        root_name = "!!root!!"
        # This is for backward compatibility when single lib version download were assumed
        dependencies = [LibraryQuery(name=name, version=version) for name, version in body.libraries.items()] \
            if isinstance(body.libraries, dict) \
            else body.libraries

        resolved_libraries = await resolve_dependencies_recursive(
            from_libraries=[LibraryResolved(
                namespace="", id="", type="",
                exportedSymbol=root_name,
                apiKey=get_api_key("1.0.0-does-not-matter"),
                fingerprint="", bundle="",
                name=root_name,
                version="1.0.0-does-not-matter",
                dependencies=dependencies
            )],
            using=body.using,
            versions_cache=versions_cache,
            resolutions_cache=resolutions_cache,
            full_data_cache=full_data_cache,
            configuration=configuration,
            context=ctx
        )

        resolved_libraries = [lib for lib in resolved_libraries if lib.name != root_name]
        items_dict = {get_full_exported_symbol(d.name, d.version): [to_package_id(d.name), get_url(d)]
                      for d in resolved_libraries}

        graph = await loading_graph(
            remaining=resolved_libraries,
            items_dict=items_dict,
            resolutions_dict=resolutions_cache,
            context=ctx)

        response = LoadingGraphResponseV1(
            graphType="sequential-v1",
            lock=[Library(**lib.dict()) for lib in resolved_libraries],
            definition=graph
        )
        await ctx.info("Loading graph resolved", data=response)
        return response


@router.get("/resources/{library_id}/{version}", summary="get the entry point of a library")
async def get_entry_point(
        request: Request,
        library_id: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            action="fetch entry point",
            request=request,
            with_attributes={"library_id": library_id, "version": version}
    ) as ctx:  # type: Context

        package_name, version, max_age = await resolve_resource(library_id=library_id, input_version=version,
                                                                configuration=configuration, context=ctx)
        doc = await configuration.doc_db.get_document(
            partition_keys={"library_name": package_name},
            clustering_keys={"version_number": get_version_number_str(version)},
            owner=Constants.owner,
            headers=ctx.headers())

        path = get_path(library_id=library_id, version=version, rest_of_path=doc['bundle'])

        return await fetch_resource(path=path, max_age=max_age, configuration=configuration, context=ctx)


@router.get("/resources/{library_id}/{version}/{rest_of_path:path}", summary="get a library")
async def get_resource(
        request: Request,
        library_id: str,
        version: str,
        rest_of_path: str,
        configuration: Configuration = Depends(get_configuration)
):
    if not rest_of_path:
        return await get_entry_point(request=request, library_id=library_id, version=version,
                                     configuration=configuration)
    async with Context.start_ep(
            action="fetch resource",
            request=request,
            with_attributes={"rest_of_path": rest_of_path}
    ) as ctx:  # type: Context
        await ctx.info(f"Target resource: '{rest_of_path}'")
        _, version, max_age = await resolve_resource(library_id=library_id, input_version=version,
                                                     configuration=configuration, context=ctx)

        path = get_path(library_id=library_id, version=version, rest_of_path=rest_of_path)
        await ctx.info('forward path constructed', data={"path": path})
        return await fetch_resource(path=path, max_age=max_age, configuration=configuration, context=ctx)


@router.get("/explorer/{library_id}/{version}",
            summary="get a library",
            response_model=ExplorerResponse)
async def explorer_root(
        request: Request,
        library_id: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await explorer(request=request, library_id=library_id, version=version, rest_of_path="",
                          configuration=configuration)


@router.get("/explorer/{library_id}/{version}/{rest_of_path:path}",
            summary="get a library",
            response_model=ExplorerResponse)
async def explorer(
        request: Request,
        library_id: str,
        version: str,
        rest_of_path: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            action="get explorer's items",
            request=request,
            with_attributes={"rest_of_path": rest_of_path}
    ) as ctx:  # type: Context

        try:
            package_name = to_package_name(library_id)
        except Exception:
            raise HTTPException(status_code=400, detail=f"'{library_id}' is not a valid library id")

        path = f"generated/explorer/{package_name.replace('@', '')}/{version}/{rest_of_path}/".replace('//', '/')
        file_system = configuration.file_system
        try:
            items = await file_system.get_object(object_name=path + "items.json", headers=ctx.headers())
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            return ExplorerResponse()
        items = json.load(io.BytesIO(items))
        return ExplorerResponse(**items)
