import asyncio
import base64
import hashlib
import itertools
import json
import os
import time
import zipfile
from pathlib import Path
from shutil import which
from typing import IO
from typing import Union, List, Mapping
from uuid import uuid4

import brotli
from fastapi import HTTPException
from starlette.responses import Response

from youwol_utils import generate_headers_downstream, QueryBody, files_check_sum, shutil, log_info, log_error
from youwol_utils.clients.docdb.models import Query, WhereClause, OrderingClause
from .configurations import Configuration
from .models import FormData, PublishResponse
from .utils_indexing import format_doc_db_record, get_version_number_str

flatten = itertools.chain.from_iterable


async def fetch(request, path, file_id, storage):

    headers = generate_headers_downstream(request.headers)

    if request.headers.get("flux-mode") == "debug" and "min.js" in file_id:
        file_id_debug = file_id.replace("min.js", "js")
        try:
            return await storage.get_bytes(path="{}/{}".format(path, file_id_debug), owner=Configuration.owner,
                                           headers=headers)
        finally:
            return await storage.get_bytes(path="{}/{}".format(path, file_id), owner=Configuration.owner,
                                           headers=headers)
    return await storage.get_bytes(path="{}/{}".format(path, file_id), owner=Configuration.owner,
                                   headers=headers)


def create_tmp_folder(zip_filename):

    dir_path = Path("./tmp_zips") / str(uuid4())
    zip_path = (dir_path / zip_filename).with_suffix('.zip')
    zip_dir_name = zip_filename.split('.')[0]
    os.makedirs(dir_path)
    return dir_path, zip_path, zip_dir_name


def get_content_encoding(file_id):

    file_id = str(file_id)
    if ".json" not in file_id and ".js" in file_id or ".css" in file_id or '.data' in file_id or '.wasm' in file_id:
        return "br"
    """ 
    if ".gz" in file_id:
        return "gzip"
    if ".br" in file_id:
        return "br"
    """
    return "identity"


def get_content_type(file_id):

    if ".json" in file_id:
        return "application/json"
    if ".js" in file_id:
        return "application/javascript; charset=UTF-8"
    elif ".css" in file_id:
        return "text/css"
    elif ".woff2" in file_id:
        return "font/woff2"
    elif '.svg' in file_id:
        return "image / svg + xml"
    elif '.html' in file_id:
        return "text/html"
    elif '.wasm' in file_id:
        return 'application/wasm'
    return "application/octet-stream"


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
        raise HTTPException(status_code=500,
                            detail="loading_graph stuck: can not resolve some dependencies:"+str(not_founds))

    return [[items_dict[a] for a in to_add]] + loading_graph(downloaded + [r for r in to_add], new_deque, items_dict)


async def format_download_form(file_path: Path, base_path: Path, dir_path: Path, compress: bool, rename: str = None) \
        -> FormData:

    if compress and get_content_encoding(file_path) == "br":
        path_log = "/".join(file_path.parts[2:])
        start = time.time()
        if which('brotli'):
            log_info(f'brotlify (system) {path_log} ...')
            p = await asyncio.create_subprocess_shell(
                cmd=f'brotli {str(file_path)}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True)

            async for f in p.stderr:
                log_error(f.decode('utf-8'))
            await p.communicate()
            os.system(f'rm {str(file_path)}')
            os.system(f'mv {str(file_path)}.br {str(file_path)}')
        else:
            log_info(f'brotlify (python) {path_log}')
            start = time.time()
            compressed = brotli.compress(file_path.read_bytes())
            with file_path.open("wb") as f:
                f.write(compressed)
        log_info(f'...{path_log} => {time.time() - start} s')

    data = open(str(file_path), 'rb').read()
    path_bucket = base_path / file_path.relative_to(dir_path) if not rename else base_path / rename

    return FormData(objectName=path_bucket, objectData=data, owner=Configuration.owner,
                    objectSize=len(data), content_type=get_content_type(file_path.name),
                    content_encoding=get_content_encoding(file_path.name))


def extract_zip_file(file: IO, zip_path: Union[Path, str], dir_path: Union[Path, str], delete_original=True):

    dir_path = str(dir_path)
    with open(zip_path, 'ab') as f:
        for chunk in iter(lambda: file.read(10000), b''):
            f.write(chunk)

    compressed_size = zip_path.stat().st_size

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dir_path)

    if delete_original:
        os.remove(zip_path)

    return compressed_size


async def publish_package(file: IO, filename: str, content_encoding, configuration, headers):

    if content_encoding not in ['identity', 'brotli']:
        raise HTTPException(status_code=422, detail="Only identity and brotli encoding are accepted ")
    need_compression = content_encoding == 'identity'
    dir_path = Path("./tmp_zips") / str(uuid4())
    zip_path = (dir_path / filename).with_suffix('.zip')

    os.makedirs(dir_path)
    try:
        log_info("extract .zip file...")
        compressed_size = extract_zip_file(file, zip_path, dir_path, delete_original=False)
        log_info("...zip extracted", compressed_size=compressed_size)

        package_path = next(flatten([[Path(root) / f for f in files if f == "package.json"]
                                     for root, _, files in os.walk(dir_path)]), None)

        if package_path is None:
            raise RuntimeError("It is required for the package to include a package.json file")

        try:
            package_json = json.loads(open(package_path).read())
        except ValueError:
            raise ValueError("It was not possible to load the json file 'package.json'. Valid json file?")

        mandatory_fields = ["name", "version"]
        if any([field not in package_json for field in mandatory_fields]):
            raise ValueError(f"The package.json file needs to define the attributes {str(mandatory_fields)}")

        library_id = package_json["name"].replace("@", '')
        version = package_json["version"]
        base_path = Path('libraries') / library_id / version
        storage = configuration.storage

        paths = flatten([[Path(root) / f for f in files] for root, _, files in os.walk(dir_path)])
        paths = [p for p in paths if p != zip_path]
        form_original = await format_download_form(zip_path, base_path, package_path.parent, need_compression,
                                                   '__original.zip')
        forms = await asyncio.gather(*[
            format_download_form(path, base_path, package_path.parent, need_compression) for path in paths
            ])
        forms = list(forms) + [form_original]
        # the fingerprint in the md5 checksum of the included files after having eventually being compressed
        os.remove(zip_path)
        md5_stamp = md5_from_folder(dir_path)

        post_requests = [storage.post_object(path=form.objectName, content=form.objectData,
                                             content_type=form.content_type, owner=Configuration.owner, headers=headers)
                         for form in forms]

        log_info(f"Clean directory {str(base_path)}")
        await storage.delete_group(prefix=base_path, owner=Configuration.owner, headers=headers)

        log_info(f"Send {len(post_requests)} files to storage")
        await asyncio.gather(*post_requests)
        record = format_doc_db_record(package_path=package_path, fingerprint=md5_stamp)
        log_info("Create docdb document", record=record)
        await configuration.doc_db.create_document(record, owner=Configuration.owner, headers=headers)

        log_info("Done", md5_stamp=md5_stamp)
        return PublishResponse(name=package_json["name"], version=version, compressedSize=compressed_size,
                               id=to_package_id(package_json["name"]), fingerprint=md5_stamp,
                               url=f"{to_package_id(package_json['name'])}/{record['version']}/{record['bundle']}")
    finally:
        shutil.rmtree(dir_path)


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
    return doc_db.query(query_body=query, owner=Configuration.owner, headers=headers)


def get_query_version(doc_db, lib_name, version, headers):

    query = QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="library_name", relation="eq", term=lib_name),
                                  WhereClause(column="version_number", relation="eq",
                                              term=get_version_number_str(version))])
        )

    return doc_db.query(query_body=query, owner=Configuration.owner, headers=headers)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def post_storage_by_chunk(storage, forms: List[FormData], count, headers):

    for i, chunk in enumerate(chunks(forms, count)):
        progress = 100 * i/(len(forms)/count)
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
            paths.append(Path(subdir)/filename)
    md5_stamp = files_check_sum(paths)
    return md5_stamp


def to_package_id(package_name: str) -> str:
    b = str.encode(package_name)
    return base64.urlsafe_b64encode(b).decode()


def to_package_name(package_id: str) -> str:
    b = str.encode(package_id)
    return base64.urlsafe_b64decode(b).decode()


def get_url(document: Mapping[str, str]) -> str:
    return to_package_id(document['library_name']) + "/"+document['version'] + "/" + get_filename(document)
