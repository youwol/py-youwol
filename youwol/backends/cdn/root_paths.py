import asyncio
import functools
import itertools
import shutil
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, File, HTTPException, Form, APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils import (
    flatten, generate_headers_downstream, PackagesNotFound, IndirectPackagesNotFound,
)
from youwol_utils.clients.docdb.models import WhereClause, QueryBody, Query, SelectClause
from youwol_utils.context import Context
from .configurations import Configuration, get_configuration
from .models import (
    PublishResponse, ListLibsResponse, Release, ListVersionsResponse, SyncResponse,
    LoadingGraphResponseV1, LoadingGraphBody, DeleteBody, Library,
    ListPacksResponse, FluxPackSummary,
)
from .resources_initialization import init_resources, synchronize
from .utils import (
    extract_zip_file, to_package_id, create_tmp_folder,
    to_package_name, get_query_version, loading_graph, get_url, fetch, format_response, publish_package,
    get_query_latest, retrieve_dependency_paths,
)
from .utils_indexing import get_version_number_str

router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-backend ok"}


@router.post("/actions/publish-library",
             summary="upload a library",
             response_model=PublishResponse)
async def publish(
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


@router.get("/queries/libraries", summary="list libraries available",
            response_model=ListLibsResponse)
async def list_libraries(
        request: Request,
        namespace: str = None,
        configuration: Configuration = Depends(get_configuration),
):
    """
    WARNING: should not be used in prod: use allow filtering
    """
    response: Optional[ListLibsResponse] = None

    async with Context.start_ep(
            request=request,
            response=lambda: response
    ) as ctx:  # type: Context
        await ctx.warning(text="This should not be used in prod: use allow filtering")

        doc_db = configuration.doc_db
        query = QueryBody.parse(f"namespace={namespace}@library_name,version#1000") \
            if namespace is not None \
            else QueryBody.parse(f"@library_name,version#1000")

        query.allow_filtering = True
        resp = await doc_db.query(query_body=query, owner=Configuration.owner, headers=ctx.headers())

        data = sorted(resp["documents"], key=lambda d: d["library_name"])
        groups = []
        for k, g in itertools.groupby(data, lambda d: d["library_name"]):
            g = list(g)
            ns = {lib["namespace"] for lib in g}.pop()

            libs = sorted(g, key=lambda d: d["version_number"])
            groups.append({"name": k,
                           "namespace": ns,
                           "id": to_package_id(k),
                           "versions": [lib["version"] for lib in libs],
                           "releases": [
                               Release(version=lib['version'],
                                       version_number=int(lib['version_number']),
                                       fingerprint=lib['fingerprint'] if 'fingerprint' in lib else "")
                               for lib in libs]
                           })
        response = ListLibsResponse(libraries=[ListVersionsResponse(**d)
                                               for d in sorted(groups, key=lambda d: d["name"])])
        return response


@router.post("/actions/sync",
             summary="sync the cdn resources from the content of the given .zip file",
             response_model=SyncResponse)
async def sync(request: Request,
               file: UploadFile = File(...),
               reset: bool = False,
               configuration: Configuration = Depends(get_configuration)):
    response: Optional[SyncResponse] = None

    async with Context.start_ep(
            request=request,
            response=lambda: response
    ) as ctx:  # type: Context

        if reset:
            await asyncio.gather(configuration.doc_db.delete_table(headers=ctx.headers()),
                                 configuration.storage.delete_bucket(force_not_empty=True, headers=ctx.headers()))
            await init_resources(configuration)

        dir_path, zip_path, zip_dir_name = create_tmp_folder(file.filename)

        try:
            compressed_size = extract_zip_file(file.file, zip_path, dir_path)
            files_count, libraries_count, namespaces = await synchronize(dir_path, zip_dir_name, configuration,
                                                                         ctx.headers(), context=ctx)

            response = SyncResponse(filesCount=files_count, librariesCount=libraries_count,
                                    compressedSize=compressed_size, namespaces=namespaces)
            return response
        finally:
            shutil.rmtree(dir_path)


async def list_versions(
        name: str,
        max_results: int,
        context: Context,
        configuration: Configuration = Depends(get_configuration)):
    async with context.start(
            action="list version of package",
            with_attributes={"name": name, "max_results": max_results}
    ) as ctx:  # type: Context

        doc_db = configuration.doc_db
        query = QueryBody(
            max_results=max_results,
            select_clauses=[SelectClause(selector="versions"), SelectClause(selector="namespace")],
            query=Query(where_clause=[WhereClause(column="library_name", relation="eq", term=name)])
        )

        response = await doc_db.query(query_body=query, owner=Configuration.owner, headers=ctx.headers())

        if not response['documents']:
            raise HTTPException(status_code=404, detail=f"The library {name} does not exist")

        namespace = {d['namespace'] for d in response['documents']}.pop()
        ordered = sorted(response['documents'], key=lambda doc: doc['version_number'])
        ordered.reverse()
        return ListVersionsResponse(
            name=name, namespace=namespace, id=to_package_id(name),
            versions=[d['version'] for d in ordered],
            releases=[Release(version=d['version'],
                              version_number=int(d['version_number']),
                              fingerprint=d['fingerprint'])
                      for d in ordered]
        )


@router.get("/libraries/{library_id}", summary="list versions of a library",
            response_model=ListVersionsResponse)
async def get_library(
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


@router.delete("/libraries/{library_id}", summary="delete a library")
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
        resp_query = await doc_db.query(query_body=query, owner=configuration.owner, headers=ctx.headers())

        await asyncio.gather(*[doc_db.delete_document(doc=d, owner=Configuration.owner, headers=ctx.headers())
                               for d in resp_query["documents"]])
        return {"deletedCount": len(resp_query["documents"])}


@router.delete("/libraries", summary="delete a library")
async def delete_libraries(request: Request, body: DeleteBody, configuration: Configuration = Depends(get_configuration)):
    responses = await asyncio.gather(*[delete_library(request=request, library_id=to_package_id(name), configuration=configuration)
                                       for name in body.librariesName])
    return {"deletedCount": functools.reduce(lambda acc, e: acc + e['deletedCount'], responses, 0)}


async def delete_version_generic(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        configuration: Configuration):
    async with Context.start_ep(
            request=request,
            with_attributes={"libraryName": library_name, "version": version}
    ) as ctx:  # type: Context
        doc_db = configuration.doc_db
        storage = configuration.storage

        namespace = namespace[1:] if namespace and namespace[0] == '@' else namespace

        doc = await doc_db.get_document(
            partition_keys={"library_name": f"@{namespace}/{library_name}"},
            clustering_keys={"version_number": get_version_number_str(version)},
            owner=configuration.owner,
            headers=ctx.headers())
        await doc_db.delete_document(doc=doc, owner=Configuration.owner, headers=ctx.headers())

        if namespace != "":
            await storage.delete_group(f"libraries/{namespace}/{library_name}/{version}",
                                       owner=Configuration.owner, headers=ctx.headers())
        else:
            await storage.delete_group(f"libraries/{library_name}/{version}",
                                       owner=Configuration.owner, headers=ctx.headers())

        return {"deletedCount": 1}


@router.delete("/libraries/{namespace}/{library_name}/{version}", summary="delete a specific version")
async def delete_version_with_namespace(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):
    return await delete_version_generic(request=request, namespace=namespace, library_name=library_name,
                                        version=version, configuration=configuration)


@router.delete("/libraries/{library_name}/{version}", summary="delete a specific version")
async def delete_version_no_namespace(
        request: Request,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):
    return await delete_version_generic(request=request, namespace="", library_name=library_name,
                                        version=version, configuration=configuration)


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
                context="Failed to retrieved latest version of package(s)",
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
                                       owner=configuration.owner, headers=ctx.headers())
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


@router.get("/queries/flux-packs", summary="list packs", response_model=ListPacksResponse)
async def list_packs(
        request: Request,
        namespace=None,
        configuration: Configuration = Depends(get_configuration)):
    """
    WARNING: should not be used in prod: use allow filtering
    """

    response: Optional[ListPacksResponse] = None
    async with Context.start_ep(
            request=request,
            response=lambda: response
    ) as ctx:  # type: Context

        await ctx.warning(" should not be used in prod: use allow filtering")
        doc_db = configuration.doc_db
        where_clauses = [WhereClause(column="type", relation="eq", term="flux_pack")]
        if namespace:
            where_clauses.append(WhereClause(column="namespace", relation="eq", term=namespace))

        query = QueryBody(
            max_results=1000,
            allow_filtering=True,
            query=Query(where_clause=where_clauses)
        )
        resp = await doc_db.query(query_body=query, owner=Configuration.owner, headers=ctx.headers())

        if len(resp["documents"]) == 1000:
            raise RuntimeError("Maximum number of items return for the current query mechanism")

        latest = {lib["library_name"]: lib for lib in resp["documents"]}

        packs = [FluxPackSummary(name=doc["library_name"].split("/")[1], description=doc["description"],
                                 tags=doc["tags"], id=to_package_id(doc["library_name"]),
                                 namespace=doc["library_name"].split("/")[0][1:])
                 for doc in latest.values()]
        response = ListPacksResponse(fluxPacks=packs)
        return response


@router.delete("/namespace/{namespace}", summary="clear the cdn resources")
async def clear(
        request: Request,
        namespace: str,
        configuration: Configuration = Depends(get_configuration)):
    """
    WARNING: should not be used in prod: use allow filtering
    """
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        await ctx.warning(" should not be used in prod: use allow filtering")

        doc_db = configuration.doc_db
        storage = configuration.storage

        if not namespace:
            await asyncio.gather(doc_db.delete_table(headers=ctx.headers()),
                                 storage.delete_bucket(force_not_empty=True, headers=ctx.headers()))
            await init_resources(configuration)
            return

        query = QueryBody(
            select_clauses=[SelectClause(selector="library_name"), SelectClause(selector="version")],
            max_results=1000,
            allow_filtering=True,
            query=Query(where_clause=[WhereClause(column="namespace", relation="eq", term=namespace)])
        )
        resp_query = await doc_db.query(query_body=query, owner=Configuration.owner, headers=ctx.headers())

        await asyncio.gather(*[doc_db.delete_document(d, owner=Configuration.owner, headers=ctx.headers())
                               for d in resp_query["documents"]])
        await storage.delete_group(f"libraries/{namespace}", owner=Configuration.owner, headers=ctx.headers())


async def get_package_generic(
        request: Request,
        library_name: str,
        version: str,
        metadata: bool = False,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request,
            with_attributes={"libraryName": library_name, "version": version, "metadata": metadata}
    ) as ctx:  # type: Context

        if version == 'latest':
            versions_resp = await list_versions(name=library_name, max_results=1, context=ctx,
                                                configuration=configuration)
            version = versions_resp.versions[0]

        doc_db = configuration.doc_db

        if metadata:
            try:
                d = await doc_db.get_document(
                    partition_keys={"library_name": library_name},
                    clustering_keys={"version_number": get_version_number_str(version)},
                    owner=configuration.owner,
                    headers=ctx.headers())
                return Library(name=d["library_name"], version=d["version"], namespace=d["namespace"],
                               id=to_package_id(d["library_name"]), type=d["type"], fingerprint=d["fingerprint"])
            except HTTPException as e:
                if e.status_code == 404:
                    raise PackagesNotFound(
                        context="Failed to retrieve a package",
                        packages=[f"{library_name}#{version}"]
                    )

        headers = generate_headers_downstream(request.headers)
        storage = configuration.storage
        path = Path("libraries") / library_name.strip('@') / version / '__original.zip'
        content = await storage.get_bytes(path=path, owner=configuration.owner, headers=headers)
        return Response(content, media_type='multipart/form-data')


@router.get("/libraries/{namespace}/{library_name}/{version}", summary="retrieve original zip file of package")
async def get_package_with_namespace(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        metadata: bool = False,
        configuration: Configuration = Depends(get_configuration)):
    namespace = '@' + namespace.strip('@')
    return await get_package_generic(request=request, library_name=namespace + "/" + library_name,
                                     version=version, metadata=metadata, configuration=configuration)


@router.get("/libraries/{library_name}/{version}", summary="delete a specific version")
async def get_package_no_namespace(
        request: Request,
        library_name: str,
        version: str,
        metadata: bool = False,
        configuration: Configuration = Depends(get_configuration)):
    return await get_package_generic(request=request, library_name=library_name, version=version,
                                     metadata=metadata, configuration=configuration)


@router.get("/resources/{rest_of_path:path}", summary="get a library")
async def get_resource(request: Request,
                       rest_of_path: str,
                       configuration: Configuration = Depends(get_configuration)
                       ):
    async with Context.start_ep(
            action="fetch resource",
            request=request,
            with_attributes={"rest_of_path": rest_of_path}
    ) as ctx:  # type: Context

        parts = [p for p in rest_of_path.split('/') if p]
        version = parts[1]

        # default browser's caching time, do not apply for 'latest' and '*-next'
        max_age = "31536000"
        try:
            package_name = to_package_name(parts[0])
        except Exception:
            raise HTTPException(status_code=400, detail=f"'{parts[0]}' is not a valid asset id")

        if version == 'latest':
            await ctx.info(text="retrieve latest version")
            versions_resp = await list_versions(name=package_name, context=ctx, max_results=1000,
                                                configuration=configuration)
            version = versions_resp.versions[0]
            max_age = "60"

        if '-next' in version:
            await ctx.info("'-next' suffix => max_age set to 0")
            max_age = "0"

        forward_path = f"libraries/{package_name.replace('@', '')}/{version}/{'/'.join(parts[2:])}"

        if len(parts) == 2:
            await ctx.info(text="no resource specified => get the entry point")
            doc = await configuration.doc_db.get_document(
                partition_keys={"library_name": package_name},
                clustering_keys={"version_number": get_version_number_str(version)},
                owner=configuration.owner,
                headers=ctx.headers())
            forward_path = f"libraries/{package_name.replace('@', '')}/{version}/{doc['bundle']}"

        await ctx.info('forward path constructed', data={"path": forward_path})
        storage = configuration.storage
        file_id = forward_path.split('/')[-1]
        path = '/'.join(forward_path.split('/')[0:-1])
        script = await fetch(request, path, file_id, storage)

        return format_response(script, file_id, max_age=max_age)
