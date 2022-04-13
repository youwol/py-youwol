import asyncio
import shutil
from typing import Optional

from fastapi import UploadFile, File, HTTPException, Form, APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils import (
    flatten, PackagesNotFound, IndirectPackagesNotFound,
)
from youwol_utils.clients.docdb.models import WhereClause, QueryBody, Query
from youwol_utils.context import Context
from youwol_utils.http_clients.cdn_backend import (
    PublishResponse, ListVersionsResponse, PublishLibrariesResponse,
    LoadingGraphResponseV1, LoadingGraphBody, Library,
    ExplorerResponse, DeleteLibraryResponse
)
from youwol_cdn_backend.configurations import Configuration, Constants, get_configuration
from youwol_cdn_backend.resources_initialization import synchronize
from youwol_cdn_backend.utils import (
    extract_zip_file, to_package_id, create_tmp_folder,
    to_package_name, get_query_version, loading_graph, get_url, publish_package,
    get_query_latest, retrieve_dependency_paths, list_versions,
    fetch_resource, resolve_resource, get_path,
)
from youwol_cdn_backend.utils_indexing import get_version_number_str

router = APIRouter()


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
        storage = configuration.storage
        path = get_path(library_id=library_id, version=version, rest_of_path='__original.zip')
        await ctx.info("Original zip path retrieved", data={"path":path})
        content = await storage.get_bytes(path=path, owner=Constants.owner, headers=ctx.headers())
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
                           id=to_package_id(d["library_name"]), type=d["type"], fingerprint=d["fingerprint"])
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
        storage = configuration.storage
        library_name = to_package_name(library_id)

        doc = await doc_db.get_document(
            partition_keys={"library_name": library_name},
            clustering_keys={"version_number": get_version_number_str(version)},
            owner=Constants.owner,
            headers=ctx.headers())
        await doc_db.delete_document(doc=doc, owner=Constants.owner, headers=ctx.headers())

        path_folder = f"{library_name}/{version}"

        await asyncio.gather(
            storage.delete_group(f"libraries/{path_folder}", owner=Constants.owner, headers=ctx.headers()),
            storage.delete_group(f"generated/explorer/{path_folder}", owner=Constants.owner, headers=ctx.headers())
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
    response: Optional[LoadingGraphResponseV1] = None
    async with Context.start_ep(
            request=request,
            response=lambda: response,
            body=body
    ) as ctx:  # type: Context

        doc_db = configuration.doc_db
        libraries = {name: version for name, version in body.libraries.items()}

        await ctx.info(text=f"Start resolving loading graph: {libraries}")

        latest_queries = [name for name, version in libraries.items() if version == "latest"]
        await ctx.info(text=f"{len(latest_queries)} latest packages targeted", data={"latest": latest_queries})
        versions_resp = await asyncio.gather(*[
            list_versions(name=name, context=ctx, max_results=1000, configuration=configuration)
            for name in latest_queries
        ], return_exceptions=True)

        if any(isinstance(v, Exception) for v in versions_resp):
            packages_error = [f"{name}#latest"
                              for e, name in zip(versions_resp, latest_queries)
                              if isinstance(e, Exception)]
            await ctx.error(
                text=f"While resolving latest version: some packages are not found in the CDN ",
                data={"missingPackages": packages_error})
            raise PackagesNotFound(
                context="Failed to retrieve the latest version of package(s)",
                packages=packages_error)

        latest_versions = {name: resp.versions[0] for name, resp in zip(latest_queries, versions_resp)}
        explicit_versions = {**libraries, **latest_versions}

        await ctx.info(
            text="First pass of versioning resolution achieved",
            data={"latest_versions_only": latest_versions,
                  "resolved_versions": explicit_versions
                  },
        )

        queries = [doc_db.get_document(partition_keys={"library_name": name},
                                       clustering_keys={"version_number": get_version_number_str(version)},
                                       owner=Constants.owner, headers=ctx.headers())
                   for name, version in explicit_versions.items()]

        dependencies = await asyncio.gather(*queries, return_exceptions=True)

        if any(isinstance(v, Exception) for v in dependencies):
            packages_error = [f"{name}#{version}" for e, (name, version) in zip(dependencies, explicit_versions.items())
                              if isinstance(e, Exception)]
            await ctx.error(
                text=f"While fetching explicit version: some packages are not found in the CDN ",
                data={"missingPackages": packages_error})

            raise PackagesNotFound(context="Failed to retrieved explicit version of package(s)",
                                   packages=packages_error)

        dependencies_dict = {d["library_name"]: d for d in dependencies}

        await ctx.info(
            text="First pass resolution done",
            data={"resolvedDependencies": dependencies_dict},
        )

        async def add_missing_dependencies():
            """ It maybe the case where some dependencies are missing in the provided body,
            here we fetch using 'body.using' or the latest version of them"""

            flatten_dependencies = set(flatten([[p.split("#")[0] for p in package['dependencies']]
                                                for package in dependencies_dict.values()]))

            missing = [d for d in flatten_dependencies if d not in dependencies_dict]

            if not missing:
                return dependencies_dict

            await ctx.info(text="Start another loop to fetch missing dependencies",
                           data={"missing": missing, "retrieved": list(dependencies_dict.keys())})

            def get_dependency(dependency):
                if dependency in body.using:
                    return get_query_version(configuration.doc_db, dependency, body.using[dependency], ctx.headers())
                return get_query_latest(configuration.doc_db, dependency, ctx.headers())

            versions = await asyncio.gather(
                *[get_dependency(dependency) for dependency in missing],
                return_exceptions=True
            )
            if any(len(v["documents"]) == 0 for v in versions):
                not_found = [f"{name}#{body.using.get(name, 'latest')}" for v, name in zip(versions, missing)
                             if len(v["documents"]) == 0]
                names = [n.split("#")[0] for n in not_found]
                paths = {name: retrieve_dependency_paths(dependencies_dict, name) for name in names}
                await ctx.error(
                    text="Some packages are not found in the CDN ",
                    data={"notFound": not_found},
                )
                raise IndirectPackagesNotFound(
                    context="Failed to retrieve a version of indirect dependencies",
                    paths=paths
                )

            versions = list(flatten([d['documents'] for d in versions]))
            for version in versions:
                lib_name = version["library_name"]
                dependencies_dict[lib_name] = version

            return await add_missing_dependencies()

        await add_missing_dependencies()
        items_dict = {d["library_name"]: [to_package_id(d["library_name"]), get_url(d)]
                      for d in dependencies_dict.values()}
        r = loading_graph([], dependencies_dict.values(), items_dict)

        lock = [Library(name=d["library_name"], version=d["version"], namespace=d["namespace"],
                        id=to_package_id(d["library_name"]), type=d["type"], fingerprint=d["fingerprint"])
                for d in dependencies_dict.values()]

        response = LoadingGraphResponseV1(graphType="sequential-v1", lock=lock, definition=r)
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
            with_attributes={"library_id": library_id, "version": version }
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
    async with Context.start_ep(
            action="fetch resource",
            request=request,
            with_attributes={"rest_of_path": rest_of_path}
    ) as ctx:  # type: Context

        _, version, max_age = await resolve_resource(library_id=library_id, input_version=version,
                                                     configuration=configuration, context=ctx)

        path = get_path(library_id=library_id, version=version, rest_of_path=rest_of_path)
        await ctx.info('forward path constructed', data={"path": path})
        return await fetch_resource(path=path, max_age=max_age, configuration=configuration, context=ctx)


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
        storage = configuration.storage
        items = await storage.get_json(path + "items.json", owner=Constants.owner, headers=ctx.headers())
        return ExplorerResponse(**items)
