# future
from __future__ import annotations

# standard library
import asyncio
import hashlib
import io
import json
import tempfile
import zipfile

from collections.abc import AsyncIterable
from datetime import datetime

# typing
from typing import NamedTuple

# third parties
import brotli
import semantic_version

from aiohttp import ClientSession
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

# Youwol
import youwol

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.environment import DownloadEvent, DownloadEventType
from youwol.app.routers.local_cdn import emit_local_cdn_status

# Youwol backends
from youwol.backends.cdn import publish_package

# Youwol utilities
from youwol.utils import (
    AnyDict,
    Context,
    aiohttp_to_starlette_response,
    encode_id,
    get_content_type,
)
from youwol.utils.http_clients.cdn_backend.utils import (
    CDN_MANIFEST_FILE,
    CdnManifest,
    get_content_encoding,
)

router = APIRouter()


FILES_PYPI_HOSTED = "https://files.pythonhosted.org"
"""
Server's base path for serving pypi files.
"""
FILES_PYODIDE_HOSTED = "https://cdn.jsdelivr.net/pyodide"
"""
Server's base path for serving pyodide files.
"""

mappings = {FILES_PYPI_HOSTED: "python/pypi/files"}


class ResourceInfo(NamedTuple):
    """
    Information regarding a pyodide resource, usually constructed from its URL.
    """

    name: str
    """
    Name of the package.
    """
    version: str
    """
    Version of the package.
    """
    file: str
    """
    Associated file (beside some files in pyodide itself, the are wheels).
    """

    @staticmethod
    def from_url(url: str) -> ResourceInfo:
        """
        Extracts resource information from the given URL.

        Parameters:
            url: The URL of the resource.

        Return:
            The parsed resource information.
        """

        # e.g.:
        # https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js
        # https://cdn.jsdelivr.net/pyodide/v0.26.1/full/pyparsing-3.1.2-py3-none-any.whl
        pyodide_version = url.split("/")[-3][1:]
        if not url.endswith(".whl"):
            return ResourceInfo(
                name="pyodide", version=pyodide_version, file=url.split("/")[-1]
            )
        file = url.split("/")[-1]
        name = file.split("-")[0]
        version = file.split("-")[1]
        if len(version.split(".")) == 1:
            version = f"{version}.0.0"
        if len(version.split(".")) == 2:
            version = f"{version}.0"
        if len(version.split(".")) >= 4:
            # It is OK to remove 'alpha', 'beta', 'post', ... as the exact version is part of the filename.
            version = ".".join(version.split(".")[0:3])

        try:
            semantic_version.Version(version)
        except ValueError as exc:
            raise ValueError(
                f"Pyodide package {name} has version '{version}' "
                f"that can not be harmonized to NPM standard."
            ) from exc
        namespace = f"pyodide-{pyodide_version.replace('.', '-')}"
        return ResourceInfo(name=f"@{namespace}/{name}", version=version, file=file)


class Package(BaseModel):
    """
    Represents the 'packages' in the 'pyodide-lock.json' file.
    See *e.g.* <a href="https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide-lock.json" target="_blank>here</a>.

    It is part of the definition of :class:`StatusResponse <youwol.app.routers.python.router.StatusResponse>`.
    """

    name: str
    """
    Name of the package.
    """
    packageType: str
    """
    Package's type.
    """
    fileName: str
    """
    Wheel filename.
    """
    version: str
    """
    Version.
    """


class PyodideInfo(BaseModel):
    """
    Represents the 'info' in the 'pyodide-lock.json' file.
    See *e.g.* <a href="https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide-lock.json" target="_blank>here</a>.

    It is part of the definition of :class:`StatusResponse <youwol.app.routers.python.router.StatusResponse>`.
    """

    arch: str
    """
    Architecture of pyodide release.
    """
    platform: str
    """
    Platform of pyodide release.
    """
    python: str
    """
    Python version.
    """
    version: str
    """
    Pyodide version.
    """


class Runtime(BaseModel):
    """
    Represents the structure of the 'pyodide-lock.json' file.
    See *e.g.* <a href="https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide-lock.json" target="_blank>here</a>.

    It is part of the definition of :class:`StatusResponse <youwol.app.routers.python.router.StatusResponse>`.
    """

    info: PyodideInfo
    """
    Pyodide build information.
    """
    packages: list[Package]
    """
    List of ported packages.
    See also <a href="https://pyodide.org/en/stable/usage/packages-in-pyodide.html" target="_blank">here</a>.
    """

    @staticmethod
    def from_pyodide_lock(lock: AnyDict):
        """
        Extracts runtime information from a 'pyodide-lock.json' file content.

        Parameters:
            lock: JSON dict of 'pyodide-lock.json'

        Return:
            The parsed runtime information.
        """
        packages = [
            Package(
                name=p["name"],
                packageType=p["package_type"],
                fileName=p["file_name"],
                version=p["version"],
            )
            for p in lock["packages"].values()
        ]
        info = lock["info"]
        return Runtime(info=PyodideInfo(**info), packages=packages)


class StatusResponse(BaseModel):
    """
    Python environment status, as returned by the endpoint :func:`status <youwol.app.routers.python.router.status>`.
    """

    runtimes: list[Runtime]
    """
    List of available pyodide runtimes in the environment.
    """


async def persist_resource(
    package: ResourceInfo, content: bytes, context: Context
) -> None:
    """
    Persists a resource to the component's database for caching and distribution purposes.

    Parameters:
        package: The information of the resource to persist.
        content: The content of the resource to persist.
        context: The context object used for tracking and logging.

    """
    async with context.start(action="persist_resource") as ctx:
        await ctx.send(
            DownloadEvent(
                kind="package",
                rawId=encode_id(package.name),
                type=DownloadEventType.STARTED,
            )
        )
        package_json = {
            "name": package.name,
            "version": package.version,
            "main": package.file if package.name != "pyodide" else "pyodide.js",
            "webpm": {"type": "pyodide" if package.name != "pyodide" else "js/wasm"},
        }
        content_hash = hashlib.md5()
        content_hash.update(content)
        yw_manifest: CdnManifest = {
            "date": datetime.now().isoformat(),
            "ywVersion": youwol.__version__,
            "files": [
                {
                    "path": package.file,
                    "contentEncoding": get_content_encoding(package.file),
                    "contentType": get_content_type(package.file),
                    "hash": content_hash.hexdigest(),
                }
            ],
        }
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            package_json_data = json.dumps(package_json).encode("utf-8")
            zip_file.writestr("package.json", package_json_data)
            manifest_json_data = json.dumps(yw_manifest).encode("utf-8")
            zip_file.writestr(CDN_MANIFEST_FILE, manifest_json_data)
            zip_file.writestr(package.file, content)

        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_config = env.backends_configuration.cdn_backend
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(zip_buffer.getvalue())
            tmp_file.seek(0)
            await publish_package(
                file=tmp_file,
                filename="cdn.zip",
                configuration=cdn_config,
                clear=package.name != "pyodide",
                context=ctx,
            )
            await emit_local_cdn_status(context=ctx)
            await ctx.send(
                DownloadEvent(
                    kind="package",
                    rawId=encode_id(package.name),
                    type=DownloadEventType.SUCCEEDED,
                )
            )


async def try_local(info: ResourceInfo, context: Context) -> Response | None:
    """
    This function attempts to retrieve the specified resource from the local Content Delivery Network (CDN).
    If the resource is found, it is returned along with a header "youwol-origin" set to 'local'.
    If the resource is not found (HTTP 404 status), the function returns None;
    Other HTTPException are re-raised.

    Parameters:
        info: The information of the resource to fetch.
        context: The context object used for tracking and logging.

    Return:
        The response object containing the fetched resource or None if not found.

    Raise:
        HTTPException: If the resource is not found (HTTP 404 status).
    """
    async with context.start(action="try_local") as ctx:
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        cdn = LocalClients.get_cdn_client(env)
        try:
            resp: Response = await cdn.get_resource(
                library_id=encode_id(info.name),
                version=info.version,
                rest_of_path=info.file,
                headers=ctx.headers(),
                custom_reader=aiohttp_to_starlette_response,
            )
            # This header will most likely be mutated by `BrowserCacheStore` as CDN resources are cached in usual
            # scenarios.
            resp.headers.append("youwol-origin", "local")
            await ctx.info(
                "Resource found in local components DB",
                data={"headers": resp.headers.items()},
            )
            return resp
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            await ctx.info("Resource not found")


async def get_and_persist_resource(
    target_url: str, request: Request, context: Context
) -> Response:
    """
    This function retrieves the resource from the specified URL and persists it to the Content Delivery Network (CDN).
    If the resource is found locally in the component's database, it is returned directly.
    If the resource is not found locally, it is fetched from the URL, persisted to the component's database,
    and then streamed back to the client.

    Parameters:
        target_url: The URL of the resource to fetch.
        request: The incoming request.
        context: The context object used for tracking and logging.

    Return:
        The response object containing the fetched or streamed resource.
    """
    async with context.start(
        action="get_and_persist_resource", with_attributes={"target_url": target_url}
    ) as ctx:
        info = ResourceInfo.from_url(target_url)
        await ctx.info(f"Retrieved '{info.name}#{info.version}' resource info")
        local = await try_local(info=info, context=ctx)
        if local:
            await ctx.info(
                "Resource found in the local components DB, return it.",
                data={"headers": local.headers.items()},
            )
            return local

        await ctx.send(
            DownloadEvent(
                kind="package",
                rawId=encode_id(info.name),
                type=DownloadEventType.ENQUEUED,
            )
        )
        await ctx.info(
            "Resource not found in the local components DB, proceed to fetch & download.",
            data={"url": target_url},
        )
        black_list = ["host", "referer", "cookie"]
        headers = {h: k for h, k in request.headers.items() if h not in black_list}

        async def process_response():
            session = ClientSession(auto_decompress=False)
            # Even if 'br' is requested, we may get 'identity' (e.g. for source-maps).
            resp = await session.get(
                url=target_url, headers={**headers, "Accept-Encoding": "br"}
            )

            response_headers = dict(resp.headers.items())
            response_headers["Cache-Control"] = "no-cache, no-store"
            encoding = response_headers.get("Content-Encoding", "identity")
            await ctx.info(
                "Got headers response from pyodide remote",
                data={"headers": response_headers},
            )

            async def content_generator() -> AsyncIterable[bytes]:
                content = b""
                try:
                    async for chunk in resp.content.iter_any():
                        yield chunk
                        content += chunk
                finally:
                    await resp.release()
                    await session.close()
                #  This assertion is not done earlier as it does not compromise the response from pyodide.
                #  Only persisting the resource in local components DB won't be executed.
                if encoding not in ["br", "identity"]:
                    raise ValueError(
                        f"Resource {target_url} requires encoding 'br' or 'identity', but got '{encoding}'"
                    )
                target_encoding = get_content_encoding(info.file)
                if encoding == "br" and target_encoding == "identity":
                    content = brotli.decompress(content)
                if encoding == "identity" and target_encoding == "br":
                    content = brotli.compress(content)

                asyncio.ensure_future(
                    persist_resource(package=info, content=content, context=ctx)
                )

            return response_headers, content_generator

        headers, content_gen = await process_response()
        return StreamingResponse(content_gen(), headers=headers)


@router.get(
    "/pyodide", response_model=StatusResponse, summary="Pyodide runtimes information"
)
async def status(request: Request) -> StatusResponse:
    """
    This endpoint returns information regarding the pyodide environment.

    Parameters:
        request: Incoming request.

    Return:
        Pyodide environment status.
    """
    async with Context.start_ep(
        request=request,
    ) as ctx:
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        library_id = encode_id("pyodide")
        cdn = LocalClients.get_cdn_client(env)
        runtimes = await cdn.get_library_info(
            library_id=library_id, headers=ctx.headers()
        )
        locks: tuple[AnyDict | BaseException] = await asyncio.gather(
            *[
                cdn.get_resource(
                    library_id=library_id,
                    version=version,
                    rest_of_path="pyodide-lock.json",
                    headers=ctx.headers(),
                )
                for version in runtimes["versions"]
            ],
            return_exceptions=True,
        )
        return StatusResponse(
            runtimes=[
                Runtime.from_pyodide_lock(lock)
                for lock in locks
                if not isinstance(lock, BaseException)
            ]
        )


@router.get("/pypi/{name}/", summary="Dispatch GET.")
async def package_info(request: Request, name: str) -> JSONResponse:
    """
    Retrieves information about a Python package from PyPI.

    This endpoint fetches information about a Python package from the Python Package Index (PyPI).
    The fetched information includes details about the package and its files, the files' URL are patched to be
    intercepted by latter call to :func:`get_pypi_file <youwol.app.routers.python.router.get_pypi_file>`.

    Parameters:
        request: Incoming request.
        name: The name of the Python package to retrieve information for.

    Return:
        A JSON response containing information about the specified Python package.
    """

    async with Context.start_ep(
        request=request,
    ) as ctx:
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        url = f"https://pypi.org/simple/{name}/"
        target_redirect = (
            f"http://localhost:{env.httpPort}/{mappings[FILES_PYPI_HOSTED]}"
        )

        async with ClientSession(auto_decompress=True) as session:
            # this header is taken from `micropip` when it queries the same URL.
            headers = {"Accept": "application/vnd.pypi.simple.v1+json, */*;q=0.01"}
            async with await session.get(url=url, headers=headers) as response:
                headers_resp = dict(response.headers.items())
                content = await response.json()
                content["files"] = [
                    {**f, "url": f["url"].replace(FILES_PYPI_HOSTED, target_redirect)}
                    for f in content["files"]
                ]
                # the response has been decompressed
                headers_resp["Content-Encoding"] = "identity"
                del headers_resp["Content-Length"]
                return JSONResponse(
                    status_code=response.status, content=content, headers=headers_resp
                )


@router.get("/pyodide/{version}/{rest_of_path:path}", summary="Dispatch GET.")
async def get_pyodide_file(request: Request, version: str, rest_of_path: str):
    """
    Intercepts `GET` request to a pyodide file, forward it to
    :glob:`FILES_PYODIDE_HOSTED <youwol.app.routers.python.router.FILES_PYODIDE_HOSTED>` and eventually persist it in
    the component's database.

    Parameters:
        request: Incoming request.
        version: Target Pyodide distribution.
        rest_of_path:  The path within the Pyodide distribution to the file.

    Return:
        The resource.
    """
    url = f"{FILES_PYODIDE_HOSTED}/v{version}/full/{rest_of_path.split('/')[-1]}"

    async with Context.start_ep(
        request=request,
    ) as ctx:
        await ctx.info(text=f"Fetch pyodide resource ({rest_of_path})")
        return await get_and_persist_resource(
            target_url=url, request=request, context=ctx
        )


@router.get("/pypi/files/{rest_of_path:path}", summary="Dispatch GET.")
async def get_pypi_file(request: Request, rest_of_path: str):
    """
    Intercepts `GET` request to a pypi file, forward it to
    :glob:`FILES_PYPI_HOSTED <youwol.app.routers.python.router.FILES_PYPI_HOSTED>` and eventually persist it in
    the component's database.

    Parameters:
        request: Incoming request.
        rest_of_path: The path within the
            :glob:`FILES_PYPI_HOSTED <youwol.app.routers.python.router.FILES_PYPI_HOSTED>` server.

    Return:
        The resource.
    """
    url = f"{FILES_PYPI_HOSTED}/{rest_of_path}"

    async with Context.start_ep(
        request=request,
    ) as ctx:
        await ctx.info(text=f"Fetch pypi file resource ({rest_of_path})")
        return await get_and_persist_resource(
            target_url=url, request=request, context=ctx
        )
