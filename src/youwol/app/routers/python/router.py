# future
from __future__ import annotations

# standard library
import asyncio
import io
import json
import tempfile
import zipfile

from collections.abc import AsyncIterable

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

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.environment import DownloadEvent, DownloadEventType
from youwol.app.routers.local_cdn import emit_local_cdn_status

# Youwol backends
from youwol.backends.cdn import publish_package
from youwol.backends.cdn.utils import get_content_encoding

# Youwol utilities
from youwol.utils import AnyDict, Context, aiohttp_to_starlette_response, encode_id

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

        if not url.endswith(".whl"):
            # e.g. https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js
            return ResourceInfo(
                name="pyodide", version=url.split("/")[-3][1:], file=url.split("/")[-1]
            )
        file = url.split("/")[-1]
        name = file.split("-")[0]
        version = file.split("-")[1]

        if len(version.split(".")) == 1:
            version = f"{version}.0.0"
        if len(version.split(".")) == 2:
            version = f"{version}.0"

        try:
            semantic_version.Version(version)
        except ValueError:
            raise ValueError(
                f"Pyodide package {name} has version '{version}' "
                f"that can not be harmonized to NPM standard."
            )

        return ResourceInfo(name=name, version=version, file=file)


class Package(BaseModel):
    """
    Represents the 'packages' in the 'pyodide-lock.json' file.
    See *e.g.* <a href="https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide-lock.json" target="_blank>here</a>.

    It is part of the definition of [StatusResponse](@yw-nav-class:python.router.StatusResponse).
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

    It is part of the definition of [StatusResponse](@yw-nav-class:python.router.StatusResponse).
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

    It is part of the definition of [StatusResponse](@yw-nav-class:python.router.StatusResponse).
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
    Python environment status, as returned by the endpoint [status](@yw-nav-func:python.router.status).
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

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            package_json_data = json.dumps(package_json).encode("utf-8")
            zip_file.writestr("package.json", package_json_data)
            zip_file.writestr(package.file, content)

        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_config = env.backends_configuration.cdn_backend
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(zip_buffer.getvalue())
            tmp_file.seek(0)
            await publish_package(
                file=tmp_file,
                filename="cdn.zip",
                # brotli is misleading: it actually means that compression has been already done appropriately
                content_encoding="brotli",
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
    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
    cdn = LocalClients.get_cdn_client(env)
    try:
        resp: Response = await cdn.get_resource(
            library_id=encode_id(info.name),
            version=info.version,
            rest_of_path=info.file,
            headers=context.headers(),
            custom_reader=aiohttp_to_starlette_response,
        )
        # This header will most likely be mutated by `BrowserCacheStore` as CDN resources are cached in usual scenarios.
        resp.headers.append("youwol-origin", "local")
        return resp
    except HTTPException as e:
        if e.status_code != 404:
            raise e


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
    async with context.start(action="get_and_persist_resource") as ctx:
        info = ResourceInfo.from_url(target_url)
        local = await try_local(info=info, context=ctx)
        if local:
            return local

        await ctx.send(
            DownloadEvent(
                kind="package",
                rawId=encode_id(info.name),
                type=DownloadEventType.ENQUEUED,
            )
        )
        black_list = ["host", "referer", "cookie"]
        headers = {h: k for h, k in request.headers.items() if h not in black_list}

        async def process_response() -> AsyncIterable[bytes]:
            async with ClientSession(auto_decompress=False) as session2:
                async with await session2.get(url=target_url, headers=headers) as resp:
                    content = b""
                    async for chunk in resp.content.iter_any():
                        yield chunk
                        content += chunk
                    if resp.headers.get("Content-Encoding") != "br":
                        raise ValueError(
                            f"Resources {target_url} must be encoded with brotli"
                        )
                    if get_content_encoding(info.file) != "br":
                        content = brotli.decompress(content)

                    asyncio.ensure_future(
                        persist_resource(package=info, content=content, context=ctx)
                    )

        async with ClientSession(auto_decompress=False) as session1:
            async with await session1.head(
                url=target_url, headers=headers
            ) as resp_head:
                headers_resp = dict(resp_head.headers.items())
                headers_resp["Cache-Control"] = "no-cache, no-store"

        return StreamingResponse(process_response(), headers=headers_resp)


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
    intercepted by latter call to [get_pypi_file](@yw-nav-func:python.router.get_pypi_file).

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
    [FILES_PYODIDE_HOSTED](@yw-nav-glob:python.router.FILES_PYODIDE_HOSTED) and eventually persist it in
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
    [FILES_PYPI_HOSTED](@yw-nav-glob:python.router.FILES_PYPI_HOSTED) and eventually persist it in
    the component's database.

    Parameters:
        request: Incoming request.
        rest_of_path: The path within the [FILES_PYPI_HOSTED](@yw-nav-glob:python.router.FILES_PYPI_HOSTED) server.

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
