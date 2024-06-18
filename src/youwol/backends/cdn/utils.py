# standard library
import asyncio
import base64
import hashlib
import io
import itertools
import json
import os
import tempfile

from pathlib import Path

# typing
from typing import IO, Literal, NamedTuple, TypedDict

# third parties
import brotli
import semantic_version

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.cdn.configurations import Configuration, Constants
from youwol.backends.cdn.utils_indexing import (
    format_doc_db_record,
    get_version_number_str,
)

# Youwol utilities
from youwol.utils import (
    AnyDict,
    CommandException,
    LocalFileSystem,
    PublishPackageError,
    QueryBody,
    QueryIndexException,
    YouwolHeaders,
    YwBrowserCacheDirective,
    execute_shell_cmd,
    extract_bytes_ranges,
    generate_headers_downstream,
    get_content_type,
)
from youwol.utils.clients.cdn import files_check_sum
from youwol.utils.clients.docdb.models import (
    OrderingClause,
    Query,
    SelectClause,
    WhereClause,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import (
    ExplorerResponse,
    FileResponse,
    FolderResponse,
    FormData,
    Library,
    LibraryResolved,
    ListVersionsResponse,
    PublishResponse,
    Release,
    get_api_key,
    get_exported_symbol,
)
from youwol.utils.http_clients.cdn_backend.utils import (
    CDN_MANIFEST_FILE,
    CdnFileManifest,
    CdnManifest,
    get_content_encoding,
    get_library_type,
    is_fixed_version,
    resolve_version,
    to_std_npm_spec,
)
from youwol.utils.utils_paths import extract_zip_file

flatten = itertools.chain.from_iterable
ORIGINAL_ZIP_FILE = "__original.zip"


async def fetch(request, path, file_id, storage):
    headers = generate_headers_downstream(request.headers)
    return await storage.get_bytes(
        path=f"{path}/{file_id}", owner=Constants.owner, headers=headers
    )


def get_filename(d):
    # for flux packs type introspection requires class name not being mangled
    if "flux-pack" in d["library_id"]:
        return d["bundle"]
    if d["bundle_min"]:
        return d["bundle_min"]
    return d["bundle"]


async def prepare_files_to_post(
    base_path: Path,
    package_path: Path,
    zip_path: Path,
    paths: list[Path],
    yw_manifest: CdnManifest | None,
    context: Context,
):
    async with context.start(
        action=f"Preparation of {len(paths) + 1} files to download in minio",
        with_labels=["filesPreparation"],
    ) as ctx:
        auto_brotli_compress: Literal["none", "lib", "os"] = "none"
        if not yw_manifest:
            auto_brotli_compress = "lib"
            return_code, outputs = await execute_shell_cmd(
                cmd="brotli --version", context=context
            )
            if not return_code:
                auto_brotli_compress = "os"
            await context.info(
                f"Brotli compression using {auto_brotli_compress}",
                data={"outputs": outputs},
            )

        form_original = await format_download_form(
            file_path=zip_path,
            base_path=base_path,
            dir_path=package_path.parent,
            auto_brotli_compress=auto_brotli_compress,
            content_encoding="identity",
            content_type="application/zip",
            rename=ORIGINAL_ZIP_FILE,
            context=ctx,
        )

        def get_file_metadata(path: Path) -> CdnFileManifest | None:
            if not yw_manifest:
                return None
            relative_path = path.relative_to(package_path.parent)
            file: CdnFileManifest | None = next(
                (f for f in yw_manifest["files"] if f["path"] == str(relative_path)),
                None,
            )
            return file

        def get_download_form(path: Path):
            metadata = get_file_metadata(path)
            return format_download_form(
                file_path=path,
                base_path=base_path,
                dir_path=package_path.parent,
                auto_brotli_compress=auto_brotli_compress,
                content_encoding=(
                    metadata.get("contentEncoding", None) if metadata else None
                ),
                content_type=metadata.get("contentType", None) if metadata else None,
                rename=None,
                context=ctx,
            )

        forms = await asyncio.gather(*[get_download_form(path=path) for path in paths])
        await context.info(
            "Forms data prepared",
            data={
                "forms": [
                    {
                        "name": str(f.objectName),
                        "size": f.objectSize,
                        "encoding": f.content_encoding,
                    }
                    for f in forms
                ]
            },
        )
        return list(forms) + [form_original]


async def format_download_form(
    file_path: Path,
    base_path: Path,
    dir_path: Path,
    auto_brotli_compress: Literal["none", "lib", "os"],
    rename: str | None,
    content_encoding: Literal["identity", "br"] | None,
    content_type: str | None,
    context: Context,
) -> FormData:

    if not content_encoding:
        content_encoding = "identity"
    if not content_type:
        content_type = get_content_type(file_path.name)

    if auto_brotli_compress != "none" and get_content_encoding(file_path.name) == "br":
        # This part is for backward compatibility.
        # It is now expected that the client publishing a package does compression on its own.

        content_encoding = "br"
        if auto_brotli_compress == "lib":
            compressed = brotli.compress(file_path.read_bytes())
            with file_path.open("wb") as f:
                f.write(compressed)
        else:
            # Case `auto_brotli_compress` is 'os'
            cmd = f"brotli {file_path} && mv {file_path}.br {file_path}"
            return_code, outputs = await execute_shell_cmd(cmd=cmd, context=context)
            if return_code is not None and return_code > 0:
                raise CommandException(command=cmd, outputs=outputs)

    with open(str(file_path), "rb") as fp:
        data = fp.read()
        path_bucket = (
            base_path / file_path.relative_to(dir_path)
            if not rename
            else base_path / rename
        )
        return FormData(
            objectName=path_bucket,
            objectData=data,
            owner=Constants.owner,
            objectSize=len(data),
            content_type=content_type,
            content_encoding=content_encoding,
        )


async def publish_package(
    file: IO,
    filename: str,
    configuration: Configuration,
    context: Context,
    clear: bool = True,
):
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = (Path(temp_dir) / filename).with_suffix(".zip")

        headers = context.headers()
        compressed_size = extract_zip_file(
            file, zip_path, temp_dir, delete_original=False
        )
        await context.info(text=f"zip extracted, size={compressed_size / 1000}ko")

        package_path = next(
            flatten(
                [
                    [Path(root) / f for f in files if f == "package.json"]
                    for root, _, files in os.walk(temp_dir)
                ]
            ),
            None,
        )

        if package_path is None:
            raise PublishPackageError(
                "It is required for the package to include a 'package.json' file"
            )

        try:
            with open(package_path, encoding="UTF-8") as fp:
                package_json = json.load(fp)
        except ValueError as exc:
            raise PublishPackageError(
                "Error while loading the json file 'package.json' -> valid json file?"
            ) from exc

        mandatory_fields = ["name", "version"]
        if any(field not in package_json for field in mandatory_fields):
            raise PublishPackageError(
                f"The package.json file needs to define the attributes {str(mandatory_fields)}"
            )

        library_id = package_json["name"].replace("@", "")
        version = package_json["version"]
        parsed_version = semantic_version.Version(version)
        if (
            parsed_version.prerelease
            and parsed_version.prerelease[0] not in Constants.allowed_prerelease
        ):
            prerelease = parsed_version.prerelease[0]
            raise PublishPackageError(
                f"Prerelease '{prerelease}' not in {Constants.allowed_prerelease}"
            )

        base_path = Path("libraries") / library_id / version
        file_system = configuration.file_system

        paths_chained = flatten(
            [[Path(root) / f for f in files] for root, _, files in os.walk(temp_dir)]
        )
        paths = [p for p in paths_chained if p != zip_path]
        await context.info(
            text=f"Prepare {len(paths)} files to publish", data={"paths": paths}
        )
        yw_manifest: CdnManifest | None = None
        if (package_path.parent / CDN_MANIFEST_FILE).exists():
            with open(package_path.parent / CDN_MANIFEST_FILE, encoding="UTF-8") as fp:
                yw_manifest = json.load(fp)

        if yw_manifest:
            await context.info(
                "Manifest file retrieved", data={"yw_manifest": yw_manifest}
            )
        else:
            await context.info("No manifest file available")

        forms = await prepare_files_to_post(
            base_path=base_path,
            package_path=package_path,
            zip_path=zip_path,
            paths=paths,
            yw_manifest=yw_manifest,
            context=context,
        )
        # the fingerprint in the md5 checksum of the included files after having eventually being compressed
        os.remove(zip_path)
        md5_stamp = md5_from_folder(Path(temp_dir))
        await context.info(text=f"md5_stamp={md5_stamp}")

        async with context.start(action="Upload data in storage") as ctx:
            prefix = f"{base_path}/"
            if clear:
                async with ctx.start(
                    action=f"Clean minio directory {prefix}"
                ) as ctx_clean:
                    await file_system.remove_folder(
                        prefix=f"{prefix}",
                        raise_not_found=False,
                        headers=ctx_clean.headers(),
                    )
            else:
                await ctx.info(
                    text="Caller requested to append files to existing minio directory."
                )
            async with ctx.start(
                action=f"Send {len(forms)} files to storage"
            ) as ctx_post:
                post_requests = [
                    file_system.put_object(
                        object_id=str(form.objectName),
                        data=io.BytesIO(form.objectData),
                        content_type=form.content_type,
                        object_name=form.objectName.name,
                        content_encoding=form.content_encoding,
                        headers=ctx_post.headers(),
                    )
                    for form in forms
                ]
                await asyncio.gather(*post_requests)

        async with context.start(action="Create record in docdb") as ctx:
            record = await format_doc_db_record(
                package_path=package_path, fingerprint=md5_stamp, context=ctx
            )
            await context.info(text="Send record to docdb", data={"record": record})
            await configuration.doc_db.create_document(
                record, owner=Constants.owner, headers=headers
            )

        await context.info(text="Create explorer data", data={"record": record})
        explorer_data = await create_explorer_data(
            dir_path=package_path.parent,
            root_path=base_path,
            forms=forms,
            context=context,
        )

        def put_explorer_object(folder, items):
            path_base = f"generated/explorer/{library_id}/{version}"
            path = (
                f"{path_base}/{folder}/items.json"
                if folder and folder != "."
                else f"{path_base}/items.json"
            )

            return file_system.put_object(
                object_id=path,
                object_name=Path(path).name,
                content_type="application/json",
                content_encoding="identity",
                data=io.BytesIO(json.dumps(items.dict()).encode()),
                headers=headers,
            )

        await asyncio.gather(
            *[
                put_explorer_object(folder, items)
                for folder, items in explorer_data.items()
            ]
        )

        return PublishResponse(
            name=package_json["name"],
            version=version,
            compressedSize=compressed_size,
            id=to_package_id(package_json["name"]),
            fingerprint=md5_stamp,
            url=f"{to_package_id(package_json['name'])}/{record['version']}/{record['bundle']}",
        )


async def create_explorer_data(
    dir_path: Path, root_path: Path, forms: list[FormData], context: Context
) -> dict[str, ExplorerResponse]:
    def compute_attributes_rec(
        content: ExplorerResponse, all_data: dict[str, ExplorerResponse]
    ):
        size_files = sum(file.size for file in content.files)
        attributes = [
            compute_attributes_rec(all_data[folder.path], all_data)
            for folder in content.folders
        ]
        size_folders = [attr[0] for attr in attributes]
        count_folders = [attr[1] for attr in attributes]

        for i, folder in enumerate(content.folders):
            folder.size = size_folders[i]
        content.size = size_files + sum(size_folders)
        content.filesCount = len(content.files) + sum(count_folders)
        return [content.size, content.filesCount]

    async with context.start(
        action="create explorer data", with_attributes={"path": str(root_path)}
    ) as ctx:
        data = {}

        class Attr(NamedTuple):
            size: int
            encoding: str

        forms_data_dict: dict[str, Attr] = {
            f"{Path(form.objectName).relative_to(root_path)}": Attr(
                size=form.objectSize,
                encoding=form.content_encoding,
            )
            for form in forms
        }

        for root, folders, files in os.walk(dir_path):
            base_path = f"{Path(root).relative_to(dir_path)}"
            base_path = base_path + "/" if base_path != "." else ""
            data[base_path.rstrip("/")] = ExplorerResponse(
                size=-1,
                filesCount=-1,
                files=[
                    FileResponse(
                        name=f,
                        size=forms_data_dict[f"{base_path}{f}"].size,
                        encoding=forms_data_dict[f"{base_path}{f}"].encoding,
                    )
                    for f in files
                ],
                folders=[
                    FolderResponse(
                        name=f, size=-1, path=f"{base_path.replace('./', '')}{f}"
                    )
                    for f in folders
                ],
            )
        data[""].files.append(
            FileResponse(
                name=ORIGINAL_ZIP_FILE,
                size=forms_data_dict[ORIGINAL_ZIP_FILE].size,
                encoding=forms_data_dict[ORIGINAL_ZIP_FILE].encoding,
            )
        )
        compute_attributes_rec(data[""], data)
        await ctx.info(
            "folders tree re-constructed",
            data={k: f"{len(d.files)} file(s)" for k, d in data.items()},
        )
        return data


class FileMetadata(TypedDict):
    contentEncoding: Literal["identity", "br"] | None
    contentType: str | None


def format_response(
    content: bytes,
    metadata: FileMetadata,
    file_id: str,
    partial_content: bool,
    max_age: str = "31536000",
) -> Response:
    content_type = metadata.get("contentType", None)
    content_encoding = metadata.get("contentEncoding", get_content_encoding(file_id))
    if content_encoding not in ["identity", "br"]:
        content_encoding = get_content_encoding(file_id)

    return Response(
        status_code=206 if partial_content else 200,
        content=content,
        headers={
            "Content-Encoding": str(content_encoding),
            "Content-Type": content_type or get_content_type(file_id),
            "cache-control": f"public, max-age={max_age}",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Embedder-Policy": "require-corp",
        },
    )


def get_query(doc_db, lib_name_version, headers):
    if "#" in lib_name_version and lib_name_version.split("#")[1] != "latest":
        lib_name, version = (
            lib_name_version.split("#")[0],
            lib_name_version.split("#")[1],
        )
        return get_query_version(doc_db, lib_name, version, headers)
    return get_query_latest(doc_db, lib_name_version.split("#")[0], headers)


def get_query_latest(doc_db, lib_name, headers):
    query = QueryBody(
        max_results=1,
        query=Query(
            where_clause=[
                WhereClause(column="library_name", relation="eq", term=lib_name)
            ],
            ordering_clause=[OrderingClause(name="version_number", order="DESC")],
        ),
    )
    return doc_db.query(query_body=query, owner=Constants.owner, headers=headers)


def get_query_version(doc_db, lib_name, version, headers):
    query = QueryBody(
        max_results=1,
        query=Query(
            where_clause=[
                WhereClause(column="library_name", relation="eq", term=lib_name),
                WhereClause(
                    column="version_number",
                    relation="eq",
                    term=get_version_number_str(version),
                ),
            ]
        ),
    )

    return doc_db.query(query_body=query, owner=Constants.owner, headers=headers)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def post_storage_by_chunk(storage, forms: list[FormData], count, headers):
    for i, chunk in enumerate(chunks(forms, count)):
        progress = 100 * i / (len(forms) / count)
        print(f"post files chunk, progress: {progress}")
        print(f"chunk ${[c.objectName for c in chunk]}")
        await asyncio.gather(
            *[
                storage.post_object(
                    path=form.objectName,
                    content=form.objectData,
                    content_type=form.content_type,
                    owner=form.owner,
                    headers=headers,
                )
                for form in chunk
            ]
        )


def md5_from_file(filename: str | Path):
    sha_hash = hashlib.md5()
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha_hash.update(chunk)
    return sha_hash.hexdigest()


def md5_from_folder(dir_path: Path):
    paths = []
    for subdir, _, files in os.walk(dir_path):
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
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"'{library_id}' is not a valid library id"
        ) from exc


def get_url(lib: LibraryResolved) -> str:
    return to_package_id(lib.name) + "/" + lib.version + "/" + lib.bundle


async def list_versions(name: str, max_results: int, context: Context, configuration):
    async with context.start(
        action="list version of package",
        with_attributes={"name": name, "max_results": max_results},
    ) as ctx:
        doc_db = configuration.doc_db
        query = QueryBody(
            max_results=max_results,
            select_clauses=[
                SelectClause(selector="versions"),
                SelectClause(selector="namespace"),
            ],
            query=Query(
                where_clause=[
                    WhereClause(column="library_name", relation="eq", term=name)
                ]
            ),
        )

        response = await doc_db.query(
            query_body=query, owner=Constants.owner, headers=ctx.headers()
        )

        if not response["documents"]:
            raise HTTPException(
                status_code=404, detail=f"The library {name} does not exist"
            )

        namespace = {d["namespace"] for d in response["documents"]}.pop()
        ordered = sorted(response["documents"], key=lambda doc: doc["version_number"])
        ordered.reverse()
        return ListVersionsResponse(
            name=name,
            namespace=namespace,
            id=to_package_id(name),
            versions=[d["version"] for d in ordered],
            releases=[
                Release(
                    version=d["version"],
                    version_number=int(d["version_number"]),
                    fingerprint=d["fingerprint"],
                )
                for d in ordered
            ],
        )


async def resolve_explicit_version(
    package_name: str,
    input_version: str,
    configuration: Configuration,
    context: Context,
):
    if is_fixed_version(input_version):
        return input_version

    versions_resp = await list_versions(
        name=package_name,
        max_results=1000,
        context=context,
        configuration=configuration,
    )
    version = await resolve_version(
        name=package_name,
        input_semver=input_version,
        versions=versions_resp.versions,
        context=context,
    )
    if not version:
        raise QueryIndexException(
            query=f"requesting version {input_version} for {package_name}",
            error="No matching entries found",
        )

    return version


async def resolve_caching_max_age(semver: str, context: Context):
    """
    This function resolves the caching max age based on the provided semantic version. If the version contains "-wip"
    postfix, or it's not a fixed version, indicating a work-in-progress or non-specific version query, the caching
    max age is set to 0; otherwise, it's set to a default value of one year (31536000 seconds).

    Parameters:
        semver: The semantic versioning string for which the caching max age needs to be resolved.
        context: An execution context object for logging the resolution process.

    Return:
        The resolved caching max age in seconds.
    """
    if "-wip" in semver or not is_fixed_version(semver=semver):
        await context.info("WIP or semantic versioning query => max_age set to 0")
        return "0"
    return "31536000"


async def resolve_resource(
    library_id: str, input_semver: str, configuration: Configuration, context: Context
):
    """
    This function resolves a resource (library) based on the provided library identifier and semantic versioning range.
    It first converts the input_semver to a standard NPM specification
    (see [to_std_npm_spec](@yw-nav-func:to_std_npm_spec)), and returns
    the package name, semver, and caching max age.
    See [resolve_caching_max_age](@yw-nav-func:resolve_caching_max_age) regarding caching max age strategy.

    Parameters:
        library_id: The identifier of the library for which the resource needs to be resolved.
        input_semver: The semantic versioning range or fixed version number for the resource.
        configuration: The service's configuration.
        context: An execution context object for logging and tracking the resolution process.

    Return:
        A tuple containing the resolved package name, version, and caching max age.


    Raises:
    - HTTPException: If the provided semantic version cannot be parsed into an NPM specification.

    """
    package_name = to_package_name(library_id)
    try:
        semver = to_std_npm_spec(input_semver)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"The provided semver {input_semver} can not be parsed using NPM specification.",
        ) from exc

    if is_fixed_version(semver):
        max_age = await resolve_caching_max_age(semver=semver, context=context)
        return package_name, semver, max_age

    version = await resolve_explicit_version(
        package_name=package_name,
        input_version=semver,
        configuration=configuration,
        context=context,
    )
    return package_name, version, 0


async def fetch_resource(
    request: Request,
    path: str,
    max_age: str,
    configuration: Configuration,
    context: Context,
):
    range_bytes = extract_bytes_ranges(request=request)
    content, file_info = await asyncio.gather(
        configuration.file_system.get_object(
            object_id=path, ranges_bytes=range_bytes, headers=context.headers()
        ),
        configuration.file_system.get_info(object_id=path, headers=context.headers()),
    )
    resp = format_response(
        content=content,
        metadata=file_info.get("metadata", {}),
        partial_content=bool(range_bytes),
        file_id=path.split("/")[-1],
        max_age=max_age,
    )
    if isinstance(configuration.file_system, LocalFileSystem):
        directive = YwBrowserCacheDirective(
            service="cdn-backend",
            filepath=f"{configuration.file_system.root_path}/{path}",
        )
        YouwolHeaders.set_yw_browser_cache_directive(directive=directive, response=resp)
    return resp


def get_path(library_id: str, version: str, rest_of_path: str):
    name = to_package_name(library_id)
    return f"libraries/{name.replace('@', '')}/{version}/{rest_of_path}"


def library_model_from_doc(d: AnyDict):
    return Library(
        name=d["library_name"],
        version=d["version"],
        namespace=d["namespace"],
        id=to_package_id(d["library_name"]),
        type=get_library_type(d["type"]),
        fingerprint=d["fingerprint"],
        exportedSymbol=get_exported_symbol(d["library_name"]),
        aliases=d.get("aliases", []),
        apiKey=get_api_key(d["version"]),
    )
