import asyncio
import functools
import itertools
import shutil
from pathlib import Path

from fastapi import UploadFile, File, HTTPException, Form, APIRouter, Depends

from starlette.requests import Request
from starlette.responses import Response

from .configurations import Configuration, get_configuration
from .models import (
    PublishResponse, ListLibsResponse, Release, ListVersionsResponse, SyncResponse,
    LoadingGraphResponseV1, LoadingGraphBody, DeleteBody, Library, DependenciesResponseV1, DependenciesLatestBody,
    ListPacksResponse, FluxPackSummary,
    )
from .resources_initialization import init_resources, synchronize
from .utils import (
    extract_zip_file, to_package_id, create_tmp_folder,
    to_package_name, get_query_version, loading_graph, get_url, fetch, format_response, publish_package,
    get_query_latest,
    )
from youwol_utils import (
    flatten, generate_headers_downstream, log_info, PackagesNotFound,
    )
from youwol_utils.clients.docdb.models import WhereClause, QueryBody, Query, SelectClause
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

    headers = generate_headers_downstream(request.headers)
    return await publish_package(file.file, file.filename, content_encoding, configuration, headers)


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

    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    query = QueryBody.parse(f"namespace={namespace}@library_name,version#1000") \
        if namespace is not None \
        else QueryBody.parse(f"@library_name,version#1000")

    query.allow_filtering = True
    response = await doc_db.query(query_body=query, owner=Configuration.owner, headers=headers)

    data = sorted(response["documents"], key=lambda d: d["library_name"])
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
                                   fingerprint=lib['fingerprint'] if 'fingerprint' in lib else "")
                           for lib in libs]
                       })

    return ListLibsResponse(libraries=[ListVersionsResponse(**d)
                                       for d in sorted(groups,  key=lambda d: d["name"])])


@router.post("/actions/sync",
             summary="sync the cdn resources from the content of the given .zip file",
             response_model=SyncResponse)
async def sync(request: Request,
               file: UploadFile = File(...),
               reset: bool = False,
               configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)

    if reset:
        await asyncio.gather(configuration.doc_db.delete_table(headers=headers),
                             configuration.storage.delete_bucket(force_not_empty=True, headers=headers))
        await init_resources(configuration)

    dir_path, zip_path, zip_dir_name = create_tmp_folder(file.filename)

    try:
        compressed_size = extract_zip_file(file.file, zip_path, dir_path)
        files_count, libraries_count, namespaces = await synchronize(dir_path, zip_dir_name, configuration, headers)

        return SyncResponse(filesCount=files_count, librariesCount=libraries_count, compressedSize=compressed_size,
                            namespaces=namespaces)
    finally:
        shutil.rmtree(dir_path)


@router.get("/queries/library", summary="list versions of a library",
            response_model=ListVersionsResponse)
async def list_versions(
        request: Request,
        name: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    query = QueryBody(
        max_results=1000,
        select_clauses=[SelectClause(selector="versions"), SelectClause(selector="namespace")],
        query=Query(where_clause=[WhereClause(column="library_name", relation="eq", term=name)])
        )

    response = await doc_db.query(query_body=query, owner=Configuration.owner, headers=headers)

    if not response['documents']:
        raise HTTPException(status_code=404, detail=f"The library {name} does not exist")

    namespace = {d['namespace'] for d in response['documents']}.pop()
    ordered = sorted(response['documents'], key=lambda doc: doc['version_number'])
    ordered.reverse()
    return ListVersionsResponse(name=name, namespace=namespace, id=to_package_id(name),
                                versions=[d['version'] for d in ordered],
                                releases=[Release(version=d['version'], fingerprint=d['fingerprint'])
                                          for d in ordered])


@router.get("/libraries/{library_id}", summary="list versions of a library",
            response_model=ListVersionsResponse)
async def get_library(
        request: Request,
        library_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    name = to_package_name(library_id)
    return await list_versions(request=request, name=name, configuration=configuration)


@router.delete("/libraries/{library_id}", summary="delete a library")
async def delete_library(
        request: Request,
        library_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    name = to_package_name(library_id)
    query = QueryBody(
        max_results=100,
        query=Query(where_clause=[WhereClause(column="library_name", relation="eq", term=name)])
        )
    resp_query = await doc_db.query(query_body=query, owner=configuration.owner, headers=headers)

    await asyncio.gather(*[doc_db.delete_document(doc=d, owner=Configuration.owner, headers=headers)
                           for d in resp_query["documents"]])
    return {"deletedCount": len(resp_query["documents"])}


@router.delete("/libraries", summary="delete a library")
async def delete_libraries(request: Request, body: DeleteBody):

    responses = await asyncio.gather(*[delete_library(request=request, library_id=to_package_id(name))
                                       for name in body.librariesName])
    return {"deletedCount": functools.reduce(lambda acc, e: acc + e['deletedCount'], responses, 0)}


async def delete_version_generic(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        configuration: Configuration):
    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    storage = configuration.storage

    namespace = namespace[1:] if namespace and namespace[0] == '@' else namespace

    doc = await doc_db.get_document(
        partition_keys={"library_name": f"@{namespace}/{library_name}"},
        clustering_keys={"version_number": get_version_number_str(version)},
        owner=configuration.owner,
        headers=headers)
    await doc_db.delete_document(doc=doc, owner=Configuration.owner, headers=headers)

    if namespace != "":
        await storage.delete_group(f"libraries/{namespace}/{library_name}/{version}",
                                   owner=Configuration.owner, headers=headers)
    else:
        await storage.delete_group(f"libraries/{library_name}/{version}",
                                   owner=Configuration.owner, headers=headers)

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

    doc_db = configuration.doc_db
    headers = generate_headers_downstream(request.headers)
    libraries = {name: version for name, version in body.libraries.items()}

    log_info(f"Start resolving loading graph: {libraries}")

    latest_queries = [name for name, version in libraries.items() if version == "latest"]
    versions_resp = await asyncio.gather(*[
        list_versions(request=request, name=name, configuration=configuration)
        for name in latest_queries
        ], return_exceptions=True)

    if any(isinstance(v, Exception) for v in versions_resp):
        packages_error = [f"{name}#latest"
                          for e, name in zip(versions_resp, latest_queries)
                          if isinstance(e, Exception)]
        raise PackagesNotFound(
            detail="Failed to retrieved latest version of package(s)",
            packages=packages_error)

    latest_versions = {name: resp.versions[0] for name, resp in zip(latest_queries, versions_resp)}
    explicit_versions = {**libraries, **latest_versions}

    log_info(f"Latest versions resolved", latest_versions=latest_versions, explicit_versions=explicit_versions)

    queries = [doc_db.get_document(partition_keys={"library_name": name},
                                   clustering_keys={"version_number": get_version_number_str(version)},
                                   owner=configuration.owner, headers=headers)
               for name, version in explicit_versions.items()]

    dependencies = await asyncio.gather(*queries, return_exceptions=True)

    if any(isinstance(v, Exception) for v in dependencies):
        packages_error = [f"{name}#{version}" for e, (name, version) in zip(dependencies, explicit_versions.items())
                          if isinstance(e, Exception)]
        raise PackagesNotFound(detail="Failed to retrieved explicit version of package(s)",
                               packages=packages_error)

    dependencies_dict = {d["library_name"]: d for d in dependencies}

    async def add_missing_dependencies(missing_previous_loop=None):
        """ It maybe the case where some dependencies are missing in the provided body,
        here we fetch using 'body.using' or the latest version of them"""
        flatten_dependencies = set(flatten([[p.split("#")[0] for p in package['dependencies']]
                                            for package in dependencies_dict.values()]))

        missing = [d for d in flatten_dependencies if d not in dependencies_dict]
        if not missing:
            return dependencies_dict

        if missing_previous_loop and missing == missing_previous_loop:
            raise PackagesNotFound(
                detail="Indirect dependencies not found in the CDN",
                packages=missing
                )

        def get_dependency(dependency):
            if dependency in body.using:
                return get_query_version(configuration.doc_db, dependency, body.using[dependency], headers)
            return get_query_latest(configuration.doc_db, dependency, headers)

        versions = await asyncio.gather(
            *[get_dependency(dependency) for dependency in missing],
            return_exceptions=True
            )
        if any(len(v["documents"]) == 0 for v in versions):
            raise PackagesNotFound(
                detail="Failed to retrieve a version of indirect dependencies",
                packages=[f"{name}#{body.using.get(name,'latest')}"
                          for v, name in zip(versions, missing)
                          if len(v["documents"]) == 0]
                )

        versions = list(flatten([d['documents'] for d in versions]))
        for version in versions:
            lib_name = version["library_name"]
            dependencies_dict[lib_name] = version

        return await add_missing_dependencies(missing_previous_loop=missing)

    await add_missing_dependencies()
    items_dict = {d["library_name"]: [to_package_id(d["library_name"]), get_url(d)]
                  for d in dependencies_dict.values()}
    r = loading_graph([], dependencies_dict.values(), items_dict)

    lock = [Library(name=d["library_name"], version=d["version"], namespace=d["namespace"],
                    id=to_package_id(d["library_name"]), type=d["type"]) for d in dependencies_dict.values()]

    return LoadingGraphResponseV1(graphType="sequential-v1", lock=lock, definition=r)

"""
@router.post("/queries/dependencies-latest", summary="get a library",
             response_model=DependenciesResponseV1)
async def resolve_dependencies_latest(
        request: Request,
        body: DependenciesLatestBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    doc_db = configuration.doc_db
    headers = generate_headers_downstream(request.headers)

    async def fetch_dependencies(libraries, fetched=None):
        if not libraries:
            return {}
        if not fetched:
            fetched = {}
        queries = [get_query(doc_db, lib, headers) for lib in libraries if lib not in fetched.keys()]
        dependencies_0 = await asyncio.gather(*queries)
        dependencies_0 = flatten([d["documents"] for d in dependencies_0])
        dependencies_0 = {d["library_name"]: d for d in dependencies_0}

        dependencies_1 = [[d.split('#')[0] for d in lib["dependencies"]] for lib in dependencies_0.values()]
        dependencies_1 = set(flatten(dependencies_1))
        return {**dependencies_0, ** await fetch_dependencies(dependencies_1, {**fetched, **dependencies_0})}

    dependencies_all = await fetch_dependencies(body.libraries)

    all_names = set(flatten([[d.split("#")[0] for d in d0["dependencies"]]
                             for d0 in dependencies_all.values()]))
    unresolved = [d for d in all_names if d not in dependencies_all]
    if unresolved:
        raise HTTPException(status_code=404, detail=f"Unresolved references in CDN: {unresolved}")

    items_dict = {d["library_name"]: [to_package_id(d["library_name"]), get_url(d)]
                  for d in dependencies_all.values()}
    r = loading_graph([], dependencies_all.values(), items_dict)
    dependencies = {v["library_name"]: v["version"] for v in dependencies_all.values()}
    lock = [Library(name=v["library_name"], version=v["version"], namespace=v["namespace"],
                    id=to_package_id(v["library_name"]), type=v["type"]) for v in dependencies_all.values()]

    return DependenciesResponseV1(libraries=dependencies,
                                  loadingGraph=LoadingGraphResponseV1(graphType="sequential-v1", lock=lock,
                                                                      definition=r))
"""


@router.get("/queries/flux-packs", summary="list packs", response_model=ListPacksResponse)
async def list_packs(
        request: Request,
        namespace=None,
        configuration: Configuration = Depends(get_configuration)):
    """
    WARNING: should not be used in prod: use allow filtering
    """
    headers = generate_headers_downstream(request.headers)
    doc_db = configuration.doc_db
    where_clauses = [WhereClause(column="type", relation="eq", term="flux_pack")]
    if namespace:
        where_clauses.append(WhereClause(column="namespace", relation="eq", term=namespace))

    query = QueryBody(
        max_results=1000,
        allow_filtering=True,
        query=Query(where_clause=where_clauses)
        )
    response = await doc_db.query(query_body=query, owner=Configuration.owner, headers=headers)

    if len(response["documents"]) == 1000:
        raise Exception("Maximum number of items return for the current query mechanism")
    latest = {lib["library_name"]: lib for lib in response["documents"]}
    packs = [FluxPackSummary(name=doc["library_name"].split("/")[1], description=doc["description"], tags=doc["tags"],
                             id=to_package_id(doc["library_name"]), namespace=doc["library_name"].split("/")[0][1:])
             for doc in latest.values()]

    return ListPacksResponse(fluxPacks=packs)


@router.delete("/namespace/{namespace}", summary="clear the cdn resources")
async def clear(
        request: Request,
        namespace: str,
        configuration: Configuration = Depends(get_configuration)):
    """
    WARNING: should not be used in prod: use allow filtering
    """
    headers = generate_headers_downstream(request.headers)

    doc_db = configuration.doc_db
    storage = configuration.storage

    if not namespace:
        await asyncio.gather(doc_db.delete_table(headers=headers),
                             storage.delete_bucket(force_not_empty=True, headers=headers))
        await init_resources(configuration)
        return

    query = QueryBody(
        select_clauses=[SelectClause(selector="library_name"), SelectClause(selector="version")],
        max_results=1000,
        allow_filtering=True,
        query=Query(where_clause=[WhereClause(column="namespace", relation="eq", term=namespace)])
        )
    resp_query = await doc_db.query(query_body=query, owner=Configuration.owner, headers=headers)

    await asyncio.gather(*[doc_db.delete_document(d, owner=Configuration.owner, headers=headers)
                           for d in resp_query["documents"]])
    await storage.delete_group(f"libraries/{namespace}", owner=Configuration.owner, headers=headers)


async def get_package_generic(
        request: Request,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    if version == 'latest':
        versions_resp = await list_versions(request=request, name=library_name, configuration=configuration)
        version = versions_resp.versions[0]

    headers = generate_headers_downstream(request.headers)
    storage = configuration.storage
    path = Path("libraries") / library_name.strip('@') / version / '__original.zip'
    content = await storage.get_bytes(path=path, owner=configuration.owner, headers=headers)
    return Response(content, media_type='multipart/form-data')


@router.get("/libraries/{namespace}/{library_name}/{version}", summary="delete a specific version")
async def get_package_with_namespace(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):
    namespace = '@'+namespace.strip('@')
    return await get_package_generic(request=request, library_name=namespace + "/"+library_name,
                                     version=version, configuration=configuration)


@router.get("/libraries/{library_name}/{version}", summary="delete a specific version")
async def get_package_no_namespace(
        request: Request,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):

    return await get_package_generic(request=request, library_name=library_name, version=version,
                                     configuration=configuration)


@router.get("/resources/{rest_of_path:path}", summary="get a library")
async def get_resource(request: Request,
                       rest_of_path: str,
                       configuration: Configuration = Depends(get_configuration)
                       ):
    # rest_of_path: $asset_id/$version/$path
    parts = rest_of_path.split('/')
    version = parts[1]
    try:
        package_name = to_package_name(parts[0])
    except Exception:
        raise HTTPException(status_code=400, detail=f"'{parts[0]}' is not a valid asset id")

    if version == 'latest':
        versions_resp = await list_versions(request=request, name=package_name, configuration=configuration)
        version = versions_resp.versions[0]

    forward_path = f"libraries/{package_name.replace('@', '')}/{version}/{'/'.join(parts[2:])}"
    storage = configuration.storage
    file_id = forward_path.split('/')[-1]
    path = '/'.join(forward_path.split('/')[0:-1])
    script = await fetch(request, path, file_id, storage)
    return format_response(script, file_id)
