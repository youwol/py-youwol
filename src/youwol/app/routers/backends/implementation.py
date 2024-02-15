# standard library
import asyncio
import functools

from asyncio.subprocess import Process
from pathlib import Path

# third parties
import aiohttp

from aiostream import stream
from fastapi import APIRouter, HTTPException
from semantic_version import Spec, Version
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.environment.proxied_backends import ProxiedBackend
from youwol.app.routers.environment.router import status
from youwol.app.routers.local_cdn.router import package_info
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import (
    Context,
    Label,
    encode_id,
    execute_shell_cmd,
    find_available_port,
    parse_json,
)

router = APIRouter()


class InstallBackendFailed(HTTPException):
    def __init__(self, return_code, outputs: list[str], ctx_id: str):
        super().__init__(
            status_code=500,
            detail={
                "exception": "InstallBackendFailed",
                "return_code": return_code,
                "outputs": outputs,
                "contextId": ctx_id,
            },
        )


class StartBackendCrashed(HTTPException):
    def __init__(self, return_code, outputs: list[str], ctx_id: str):
        super().__init__(
            status_code=500,
            detail={
                "exception": "StartBackendCrashed",
                "return_code": return_code,
                "outputs": outputs,
                "contextId": ctx_id,
            },
        )


class StartBackendTimeout(HTTPException):
    def __init__(self, outputs: list[str], ctx_id: str):
        super().__init__(
            status_code=408,
            detail={
                "exception": "StartBackendTimeout",
                "outputs": outputs,
                "contextId": ctx_id,
            },
        )


async def install_backend_shell(folder: Path, context: Context) -> list[str]:
    async with context.start(
        action="install backend", with_labels=["INSTALL_BACKEND"]
    ) as ctx:
        cmd_install = f"(cd {folder} &&  sh ./install.sh)"

        return_code, outputs = await execute_shell_cmd(cmd=cmd_install, context=ctx)
        if return_code > 0:
            (folder / "install.manifest.txt").write_text(
                functools.reduce(lambda acc, e: acc + e, outputs, "")
            )
        if return_code > 1:
            raise InstallBackendFailed(
                return_code=return_code, outputs=outputs, ctx_id=context.uid
            )
        return outputs


async def start_backend_shell(
    backend: str,
    version: str,
    folder: Path,
    port: int,
    outputs: list[str],
    context: Context,
) -> tuple[Process, str]:
    async with context.start(
        action="start backend",
        with_labels=[Label.START_BACKEND_SH],
        with_attributes={"backend": backend, "version": version},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        package_json = parse_json(folder / "package.json")
        cmd_start = (
            f"(cd {folder} &&  sh ./{package_json['main']} -p {port} -s {env.httpPort})"
        )

        await ctx.info(text=cmd_start)
        p = await asyncio.create_subprocess_shell(
            cmd=cmd_start,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )

        async def collect_outputs():
            async with stream.merge(p.stdout, p.stderr).stream() as messages_stream:
                async for message in messages_stream:
                    outputs.append(message.decode("utf-8"))
                    await ctx.info(text=outputs[-1])

            await p.communicate()

        asyncio.ensure_future(collect_outputs())
        return p, ctx.uid


async def wait_readiness(port: int, process: Process):

    url = f"http://localhost:{port}"
    while True:

        if process.returncode and process.returncode > 0:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return True
        except aiohttp.ClientError:
            pass

        await asyncio.sleep(1)


async def ensure_running(
    request: Request,
    backend_name: str,
    version_query: str,
    timeout: int,
    context: Context,
) -> ProxiedBackend:

    env = await context.get("env", YouwolEnvironment)
    backend = env.proxied_backends.get(name=backend_name, query_version=version_query)
    if backend:
        return backend

    async with context.start(action="ensure_running") as ctx:

        package = await package_info(
            request=request, package_id=encode_id(backend_name)
        )
        query_spec = Spec(version_query)

        matching_versions: list[str] = [
            version_info.version
            for version_info in package.versions
            if query_spec.match(Version(version_info.version))
        ]
        if not matching_versions:
            raise HTTPException(
                status_code=404,
                detail=f"No matching version fo  '{backend_name}' match selector ${version_query}",
            )

        latest_version_backend = sorted(matching_versions, key=Version, reverse=True)[0]
        await ctx.info(text=f"Found matching version '{latest_version_backend}'")
        folder = (
            env.pathsBook.local_cdn_storage
            / "libraries"
            / backend_name
            / latest_version_backend
        )

        install_outputs = await install_backend_shell(folder=folder, context=ctx)

        port = find_available_port(start=2010, end=3000)

        await ctx.info(text=f"Start backend from '{folder}' on port {port}")

        outputs = []
        process, std_outputs_ctx_id = await start_backend_shell(
            backend=backend_name,
            version=latest_version_backend,
            folder=folder,
            port=port,
            outputs=outputs,
            context=context,
        )

        try:
            is_ready = await asyncio.wait_for(wait_readiness(port, process), timeout)
            if not is_ready:
                await asyncio.sleep(1)
                raise StartBackendCrashed(
                    return_code=process.returncode, outputs=outputs, ctx_id=context.uid
                )

            proxy = env.proxied_backends.register(
                name=backend_name,
                version=latest_version_backend,
                port=port,
                process=process,
                install_outputs=install_outputs,
                server_outputs_ctx_id=std_outputs_ctx_id,
            )
            await status(request=request, config=env)
            return proxy
        except TimeoutError:
            process.terminate()
            raise StartBackendTimeout(outputs=outputs, ctx_id=context.uid)
