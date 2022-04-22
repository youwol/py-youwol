import asyncio
import base64
import hashlib
import itertools
import json
import os
from pathlib import Path
from typing import IO, Optional, Dict
from typing import Union, List, Mapping
from uuid import uuid4

import brotli
from fastapi import HTTPException
from starlette.responses import Response

import semantic_version
from youwol_utils import generate_headers_downstream, QueryBody, files_check_sum, shutil, \
    CircularDependencies, PublishPackageError, get_content_type
from youwol_utils.clients.docdb.models import Query, WhereClause, OrderingClause, SelectClause
from youwol_utils.context import Context
from youwol_cdn_backend.configurations import Constants, Configuration
from youwol_utils.http_clients.cdn_backend import FormData, PublishResponse, FileResponse, \
    FolderResponse, ExplorerResponse, ListVersionsResponse, Release
from youwol_cdn_backend.utils_indexing import format_doc_db_record, get_version_number_str
from youwol_utils.utils_paths import extract_zip_file

flatten = itertools.chain.from_iterable


async def fetch(request, path, file_id, storage):
    headers = generate_headers_downstream(request.headers)
    return await storage.get_bytes(path="{}/{}".format(path, file_id), owner=Constants.owner,
                                   headers=headers)


def create_tmp_folder(zip_filename):
    dir_path = Path("./tmp_zips") / str(uuid4())
    zip_path = (dir_path / zip_filename).with_suffix('.zip')
    zip_dir_name = zip_filename.split('.')[0]
    os.makedirs(dir_path)
    return dir_path, zip_path, zip_dir_name


def get_filename(d):
    # for flux packs type introspection requires class name not being mangled
    if "flux-pack" in d["library_id"]:
        return d["bundle"]
    if d["bundle_min"] != "":
        return d["bundle_min"]
    return d["bundle"]


def loading_graph(downloaded, deque, items_dict):
    dependencies = {d["library_name"]: [d2.split("#")[0] in downloaded for d2 in d["dependencies"]]
                    for d in deque}
    to_add = [name for name, dependencies_here in dependencies.items() if all(dependencies_here)]
    new_deque = [p for p in deque if p["library_name"] not in to_add]

    if len(new_deque) == 0:
        return [[items_dict[a] for a in to_add]]

    if len(new_deque) == len(deque):
        dependencies_dict = {d["library_name"]: d["dependencies"] for d in deque}
        not_founds = {pack: [dependencies_dict[pack][i] for i, found in enumerate(founds) if not found]
                      for pack, founds in dependencies.items()}
        print("Can not resolve dependency(ies)", new_deque, deque)
        raise CircularDependencies(context="Loading graph resolution stuck",
                                   packages=not_founds)

    return [[items_dict[a] for a in to_add]] + loading_graph(downloaded + [r for r in to_add], new_deque, items_dict)


async def prepare_files_to_post(base_path: Path, package_path: Path, zip_path: Path, paths: List[Path],
                                need_compression, context: Context):
    async with context.start(action=f"Preparation of {len(paths) + 1} files to download in minio",
                             with_labels=["filesPreparation"]):
        form_original = format_download_form(zip_path, base_path, package_path.parent, need_compression,
                                             '__original.zip')
        forms = [
            format_download_form(path, base_path, package_path.parent, need_compression, None)
            for path in paths
        ]
        await context.info(
            "Forms data prepared",
            data={"forms": [{"name": str(f.objectName), "size": f.objectSize, "encoding": f.content_encoding}
                            for f in forms]})
        return list(forms) + [form_original]


def format_download_form(file_path: Path, base_path: Path, dir_path: Path, compress: bool, rename: Optional[str]) \
        -> FormData:

    if compress and get_content_encoding(file_path) == "br":
        compressed = brotli.compress(file_path.read_bytes())
        with file_path.open("wb") as f:
            f.write(compressed)

    data = open(str(file_path), 'rb').read()
    path_bucket = base_path / file_path.relative_to(dir_path) if not rename else base_path / rename

    return FormData(objectName=path_bucket, objectData=data, owner=Constants.owner,
                    objectSize=len(data), content_type=get_content_type(file_path.name),
                    content_encoding=get_content_encoding(file_path.name))


async def publish_package(file: IO, filename: str, content_encoding, configuration: Configuration, context: Context):

    if content_encoding not in ['identity', 'brotli']:
        raise HTTPException(status_code=422, detail="Only identity and brotli encoding are accepted ")
    need_compression = content_encoding == 'identity'
    dir_path = Path("./tmp_zips") / str(uuid4())
    zip_path = (dir_path / filename).with_suffix('.zip')

    os.makedirs(dir_path)
    headers = context.headers()
    try:
        compressed_size = extract_zip_file(file, zip_path, dir_path, delete_original=False)
        await context.info(text=f"zip extracted, size={compressed_size / 1000}ko")

        package_path = next(flatten([[Path(root) / f for f in files if f == "package.json"]
                                     for root, _, files in os.walk(dir_path)]), None)

        if package_path is None:
            raise PublishPackageError("It is required for the package to include a 'package.json' file")

        try:
            package_json = json.loads(open(package_path).read())
        except ValueError:
            raise PublishPackageError("Error while loading the json file 'package.json' -> valid json file?")

        mandatory_fields = ["name", "version"]
        if any([field not in package_json for field in mandatory_fields]):
            raise PublishPackageError(f"The package.json file needs to define the attributes {str(mandatory_fields)}")

        library_id = package_json["name"].replace("@", '')
        version = package_json["version"]
        parsed_version = semantic_version.Version(version)
        if parsed_version.prerelease and parsed_version.prerelease[0] not in Constants.allowed_prerelease:
            prerelease = parsed_version.prerelease[0]
            raise PublishPackageError(f"Prerelease '{prerelease}' not in {Constants.allowed_prerelease}")

        base_path = Path('libraries') / library_id / version
        storage = configuration.storage

        paths = flatten([[Path(root) / f for f in files] for root, _, files in os.walk(dir_path)])
        paths = [p for p in paths if p != zip_path]
        await context.info(text=f"Prepare {len(paths)} files to publish", data={"paths": paths})

        forms = await prepare_files_to_post(base_path=base_path, package_path=package_path, zip_path=zip_path,
                                            paths=paths, need_compression=need_compression, context=context)
        # the fingerprint in the md5 checksum of the included files after having eventually being compressed
        os.remove(zip_path)
        md5_stamp = md5_from_folder(dir_path)
        await context.info(text=f"md5_stamp={md5_stamp}")

        post_requests = [storage.post_object(path=form.objectName, content=form.objectData,
                                             content_type=form.content_type, owner=Constants.owner, headers=headers)
                         for form in forms]

        async with context.start(action="Upload data in storage"):
            await context.info(text=f"Clean minio directory {str(base_path)}")
            await storage.delete_group(prefix=base_path, owner=Constants.owner, headers=headers)
            await context.info(text=f"Send {len(post_requests)} files to storage")
            await asyncio.gather(*post_requests)

        async with context.start(action="Create record in docdb"):
            record = format_doc_db_record(package_path=package_path, fingerprint=md5_stamp)
            await context.info(text=f"Send record to docdb", data={"record": record})
            await configuration.doc_db.create_document(record, owner=Constants.owner, headers=headers)

        await context.info(text=f"Create explorer data", data={"record": record})
        explorer_data = await create_explorer_data(dir_path=package_path.parent, root_path=base_path, forms=forms,
                                                   context=context)

        def get_explorer_path(folder):
            base = f"generated/explorer/{library_id}/{version}"
            return f"{base}/{folder}/items.json" if folder and folder != '.' else f"{base}/items.json"

        await asyncio.gather(*[storage.post_json(path=get_explorer_path(folder), json=items.dict(),
                                                 owner=Constants.owner, headers=headers)
                               for folder, items in explorer_data.items()])

        return PublishResponse(name=package_json["name"], version=version, compressedSize=compressed_size,
                               id=to_package_id(package_json["name"]), fingerprint=md5_stamp,
                               url=f"{to_package_id(package_json['name'])}/{record['version']}/{record['bundle']}")
    finally:
        shutil.rmtree(dir_path)


async def create_explorer_data(dir_path: Path, root_path: Path, forms: List[FormData], context: Context)\
        -> Dict[str, ExplorerResponse]:

    def compute_folders_size_rec(content: ExplorerResponse, all_data, result):

        size_files = sum([file.size for file in content.files])
        size_folders = [compute_folders_size_rec(all_data[folder.path], all_data, result)
                        for folder in content.folders]

        for i, folder in enumerate(content.folders):
            folder.size = size_folders[i]
        content.size = size_files + sum(size_folders)
        return content.size

    async with context.start(action="create explorer data",
                             with_attributes={"path": str(root_path)}
                             ) as ctx:  # type: Context
        data = {}
        forms_data_dict = {f"{Path(form.objectName).relative_to(root_path)}": {
            "size": form.objectSize,
            "encoding": form.content_encoding
        } for form in forms}

        for root, folders, files in os.walk(dir_path):
            base_path = f"{Path(root).relative_to(dir_path)}".lstrip('./')
            base_path = base_path + "/" if base_path else base_path
            data[base_path.rstrip('/')] = ExplorerResponse(
                size=-1,
                files=[FileResponse(name=f, **forms_data_dict[f"{base_path}{f}"]) for f in files],
                folders=[FolderResponse(name=f, size=-1, path=f"{base_path}{f}") for f in folders],
            )
        data[''].files.append(FileResponse(name="__original.zip", **forms_data_dict["__original.zip"]))
        results = {}
        compute_folders_size_rec(data[''], data, results)
        await ctx.info('folders tree re-constructed', data={k: f"{len(d.files)} file(s)" for k, d in data.items()})
        return data


def get_content_encoding(file_id):
    file_id = str(file_id)
    if ".json" not in file_id and ".js" in file_id or ".css" in file_id or '.data' in file_id or '.wasm' in file_id:
        return "br"

    return "identity"


def format_response(content: bytes, file_id: str, max_age: str = "31536000") -> Response:
    return Response(
        content=content,
        headers={
            "Content-Encoding": get_content_encoding(file_id),
            "Content-Type": get_content_type(file_id),
            "cache-control": f"public, max-age={max_age}",
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Embedder-Policy': 'require-corp'
        }
    )


def get_query(doc_db, lib_name_version, headers):
    if '#' in lib_name_version and lib_name_version.split('#')[1] != "latest":
        lib_name, version = lib_name_version.split('#')[0], lib_name_version.split('#')[1]
        return get_query_version(doc_db, lib_name, version, headers)
    return get_query_latest(doc_db, lib_name_version.split('#')[0], headers)


def get_query_latest(doc_db, lib_name, headers):
    query = QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="library_name", relation="eq", term=lib_name)],
                    ordering_clause=[OrderingClause(name="version_number", order="DESC")])
    )
    return doc_db.query(query_body=query, owner=Constants.owner, headers=headers)


def get_query_version(doc_db, lib_name, version, headers):
    query = QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="library_name", relation="eq", term=lib_name),
                                  WhereClause(column="version_number", relation="eq",
                                              term=get_version_number_str(version))])
    )

    return doc_db.query(query_body=query, owner=Constants.owner, headers=headers)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def post_storage_by_chunk(storage, forms: List[FormData], count, headers):
    for i, chunk in enumerate(chunks(forms, count)):
        progress = 100 * i / (len(forms) / count)
        print(f"post files chunk, progress: {progress}")
        print(f"chunk ${[c.objectName for c in chunk]}")
        await asyncio.gather(*[storage.post_object(path=form.objectName, content=form.objectData,
                                                   content_type=form.content_type, owner=form.owner, headers=headers)
                               for form in chunk])


def md5_from_file(filename: Union[str, Path]):
    sha_hash = hashlib.md5()
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha_hash.update(chunk)
    return sha_hash.hexdigest()


def md5_from_folder(dir_path: Path):
    paths = []
    for subdir, dirs, files in os.walk(dir_path):
        for filename in files:
            paths.append(Path(subdir) / filename)
    md5_stamp = files_check_sum(paths)
    return md5_stamp


def to_package_id(package_name: str) -> str:
    b = str.encode(package_name)
    return base64.urlsafe_b64encode(b).decode()


def to_package_name(library_id: str) -> str:
    try:
        b = str.encode(library_id)
        return base64.urlsafe_b64decode(b).decode()
    except Exception:
        raise HTTPException(status_code=400, detail=f"'{library_id}' is not a valid library id")


def get_url(document: Mapping[str, str]) -> str:
    return to_package_id(document['library_name']) + "/" + document['version'] + "/" + get_filename(document)


def retrieve_dependency_paths(dependencies_dict, from_package: str, suffix: str = None) -> List[str]:
    parents = [name for name, data in dependencies_dict.items()
               if any([dep_id.split("#")[0] == from_package for dep_id in data['dependencies']])]
    if not parents:
        return [f"{from_package} > {suffix}"]
    paths = [retrieve_dependency_paths(dependencies_dict, parent,
                                       f"{from_package} > {suffix}" if suffix else from_package)
             for parent in parents]
    paths = list(itertools.chain.from_iterable(paths))
    return paths


async def list_versions(
        name: str,
        max_results: int,
        context: Context,
        configuration):
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

        response = await doc_db.query(query_body=query, owner=Constants.owner, headers=ctx.headers())

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


async def resolve_explicit_version(package_name: str, input_version: str, configuration: Configuration,
                                   context: Context):
    if input_version == 'latest':
        await context.info(text="retrieve latest version")
        versions_resp = await list_versions(name=package_name, context=context, max_results=1,
                                            configuration=configuration)
        return versions_resp.versions[0]
    return input_version


async def resolve_caching_max_age(version: str, context: Context):
    if "-wip" in version:
        await context.info("'-wip' suffix => max_age set to 0")
        return "0"
    return "31536000"


async def resolve_resource(library_id: str, input_version: str, configuration: Configuration,
                           context: Context):

    package_name = to_package_name(library_id)
    version = await resolve_explicit_version(package_name=package_name, input_version=input_version,
                                             configuration=configuration, context=context)
    max_age = await resolve_caching_max_age(version=version, context=context)
    return package_name, version, max_age


async def fetch_resource(path: str, max_age: str, configuration: Configuration, context: Context):
    content = await configuration.storage.get_bytes(
        path=path,
        owner=Constants.owner,
        headers=context.headers())

    return format_response(content=content, file_id=path.split('/')[-1], max_age=max_age)


def get_path(library_id: str, version: str, rest_of_path: str):
    name = to_package_name(library_id)
    return f"libraries/{name.replace('@', '')}/{version}/{rest_of_path}"
