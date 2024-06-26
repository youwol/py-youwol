# standard library
import asyncio
import functools
import uuid

from asyncio.subprocess import Process
from pathlib import Path

# typing
from typing import Literal

# third parties
import aiohttp

from aiostream import stream
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from semantic_version import Spec, Version
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.environment.proxied_backends import (
    DEFAULT_PARTITION_ID,
    ProxiedBackend,
    ProxiedBackendConfiguration,
    get_build_fingerprint,
)
from youwol.app.routers.environment import AssetsDownloader
from youwol.app.routers.environment.router import emit_environment_status
from youwol.app.routers.local_cdn.router import package_info
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import (
    Context,
    Label,
    clone_environ,
    encode_id,
    execute_shell_cmd,
    find_available_port,
    parse_json,
)

router = APIRouter()

INSTALL_MANIFEST_FILE = "install.manifest.txt"


class DownloadBackendEvent(BaseModel):
    """
    Represents an event associated to a backend start.
    """

    name: str
    """
    Name of the backend.
    """

    version: str
    """
    Version of the backend.
    """

    event: Literal["started", "succeeded", "failed"]
    """
    Event type.
    """


class InstallBackendEvent(BaseModel):
    """
    Represents an event associated to a backend installation.
    """

    installId: str
    """
    Unique ID for the installation flow
    """

    name: str
    """
    Name of the backend.
    """

    version: str
    """
    Version of the backend.
    """

    event: Literal["started", "failed", "succeeded"]
    """
    Event type.
    """


class StartBackendEvent(BaseModel):
    """
    Represents an event associated to a backend start.
    """

    uid: str | None
    """
    Backend's uid, available for event `listening`.
    """

    partitionId: str
    """
    Encapsulating partition.
    """

    name: str
    """
    Name of the backend.
    """

    version: str
    """
    Version of the backend.
    """

    event: Literal["starting", "listening", "failed"]
    """
    Event type.
    """


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


def install_manifest_name(build_fingerprint):
    if build_fingerprint is None:
        return INSTALL_MANIFEST_FILE
    return INSTALL_MANIFEST_FILE.replace(".txt", f".{build_fingerprint}.txt")


async def install_backend_shell(
    folder: Path,
    name: str,
    version: str,
    config: ProxiedBackendConfiguration,
    context: Context,
) -> list[str]:

    uid = str(uuid.uuid4())
    build_fingerprint = get_build_fingerprint(config)

    def get_build_args():
        return functools.reduce(
            lambda acc, e: f"{acc} --{e[0]} '{e[1]}'",
            config.build.items(),
            f"--fingerprint {build_fingerprint}",
        )

    async with context.start(
        action="install backend",
        with_labels=[Label.INSTALL_BACKEND_SH],
        with_attributes={"name": name, "version": version, "installId": uid},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        await ctx.send(
            InstallBackendEvent(
                name=name, version=version, event="started", installId=uid
            )
        )
        build_args = get_build_args()

        cmd_install = f"(cd {folder} &&  sh ./install.sh {build_args})"

        return_code, outputs = await execute_shell_cmd(cmd=cmd_install, context=ctx)
        if return_code > 1:
            await ctx.send(
                InstallBackendEvent(
                    name=name, version=version, event="failed", installId=uid
                )
            )
            raise InstallBackendFailed(
                return_code=return_code, outputs=outputs, ctx_id=context.uid
            )
        manifest_name = install_manifest_name(build_fingerprint)
        (folder / manifest_name).write_text(
            functools.reduce(lambda acc, e: acc + e, outputs, "")
        )
        # Update latest manifest
        (folder / INSTALL_MANIFEST_FILE).write_text(
            functools.reduce(lambda acc, e: acc + e, outputs, "")
        )
        await ctx.send(
            InstallBackendEvent(
                name=name, version=version, event="succeeded", installId=uid
            )
        )
        return outputs


async def start_backend_shell(
    name: str,
    version: str,
    config: ProxiedBackendConfiguration,
    folder: Path,
    port: int,
    outputs: list[str],
    context: Context,
) -> tuple[Process, str]:
    async with context.start(
        action="start backend",
        with_labels=[Label.START_BACKEND_SH],
        with_attributes={"name": name, "version": version},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        package_json = parse_json(folder / "package.json")
        entry_sh = package_json["main"]
        build_arg = f" -b {get_build_fingerprint(config)}"

        cmd_start = (
            f"(cd {folder} &&  sh ./{entry_sh} -p {port} -s {env.httpPort} {build_arg})"
        )

        await ctx.info(text=cmd_start)
        p = await asyncio.create_subprocess_shell(
            cmd=cmd_start,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
            env=clone_environ(env_variables={"PYTHONPATH": ""}),
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
    partition_id: str,
    backend_name: str,
    version_query: str,
    config: ProxiedBackendConfiguration | None,
    timeout: int,
    context: Context,
) -> ProxiedBackend:
    """
    The `config == None` means: take corresponding service if running whatever its configuration.

    :param request:
    :param partition_id:
    :param backend_name:
    :param version_query:
    :param config:
    :param timeout:
    :param context:
    :return:
    """
    env = await context.get("env", YouwolEnvironment)

    async with context.start(
        action="ensure_running",
        with_attributes={"name": backend_name, "version query": version_query},
    ) as ctx:
        if config is None:
            await ctx.info(
                f"Backend {backend_name}#{version_query} with any config accepted."
            )
        else:
            await ctx.info(
                f"Backend {backend_name}#{version_query} with only given config accepted.",
                data={"config": config},
            )

        backend = env.proxied_backends.query_latest(
            partition_id=partition_id, name=backend_name, query_version=version_query
        )
        if backend and config in (backend.configuration, None):
            await ctx.info("Matching backend already running.")
            await ctx.send(
                data=StartBackendEvent(
                    uid=backend.uid,
                    partitionId=backend.partition_id,
                    name=backend_name,
                    version=backend.version,
                    event="listening",
                )
            )
            return backend

        if backend and backend.partition_id == DEFAULT_PARTITION_ID:
            # Within the default partition ID, used *e.g.* for dev. server, a mismatch in config is tolerated.
            await ctx.info(
                "Matching backend in 'Default' partition available, returning it even if config. mismatch"
            )
            return backend

        if backend:
            await ctx.info(
                f"Running backend {backend.name}#{backend.version} mismatch w/ config. => terminate it",
                data={"config": config},
            )
            await env.proxied_backends.terminate(uid=backend.uid, context=ctx)
            await emit_environment_status(context=ctx)

        if not config:
            await ctx.info(
                "No config provided, and no matching backend running => use default configuration"
            )
            config = ProxiedBackendConfiguration()

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
                detail=f"No matching version for '{backend_name}' match selector {version_query}",
            )

        latest_version_backend = sorted(matching_versions, key=Version, reverse=True)[0]
        await ctx.info(text=f"Found matching version '{latest_version_backend}'")
        folder = env.pathsBook.local_cdn_component(
            name=backend_name, version=latest_version_backend
        )
        fp = get_build_fingerprint(config)

        if not (folder / install_manifest_name(fp)).exists():
            await ctx.info(f"No install manifest found for build fingerprint {fp}")
            install_outputs = await install_backend_shell(
                folder=folder,
                name=backend_name,
                version=latest_version_backend,
                config=config,
                context=ctx,
            )
        else:
            await ctx.info(f"Install manifest found for build fingerprint {fp}")
            install_outputs = [f"Backend {backend_name} already installed"]
        port = find_available_port(start=2010, end=3000)

        await ctx.info(text=f"Start backend from '{folder}' on port {port}")

        outputs = []
        await ctx.send(
            data=StartBackendEvent(
                partitionId=partition_id,
                name=backend_name,
                version=latest_version_backend,
                event="starting",
            )
        )
        process, std_outputs_ctx_id = await start_backend_shell(
            name=backend_name,
            version=latest_version_backend,
            config=config,
            folder=folder,
            port=port,
            outputs=outputs,
            context=ctx,
        )

        try:
            is_ready = await asyncio.wait_for(wait_readiness(port, process), timeout)
            if not is_ready:
                await asyncio.sleep(1)
                await ctx.send(
                    data=StartBackendEvent(
                        partitionId=partition_id,
                        name=backend_name,
                        version=latest_version_backend,
                        event="failed",
                    )
                )
                raise StartBackendCrashed(
                    return_code=process.returncode, outputs=outputs, ctx_id=context.uid
                )

            proxy = env.proxied_backends.register(
                partition_id=partition_id,
                name=backend_name,
                version=latest_version_backend,
                configuration=config,
                port=port,
                process=process,
                install_outputs=install_outputs,
                server_outputs_ctx_id=std_outputs_ctx_id,
            )
            await ctx.send(
                data=StartBackendEvent(
                    uid=proxy.uid,
                    partitionId=proxy.partition_id,
                    name=proxy.name,
                    version=proxy.version,
                    event="listening",
                )
            )
            await emit_environment_status(context=ctx)
            return proxy
        except TimeoutError as exc:
            process.terminate()
            raise StartBackendTimeout(outputs=outputs, ctx_id=context.uid) from exc


class DownloadBackendFailed(Exception):
    """
    Exception raised when backend downloading failed.
    """

    def __init__(self, name: str, version: str, context_id: str):
        """
        Initializes the instance.

        Parameters:
            name: The name of the backend.
            version: The specific version of the backend.
            context_id: Context ID referencing the function that handled the download.
        """
        super().__init__(f"Backend '{name}' at version {version} failed to download.")
        self.context_id = context_id
        self.name = name
        self.version = version


async def download_install_backend(
    backend_name: str,
    url: str,
    version: str,
    config: ProxiedBackendConfiguration,
    context: Context,
) -> None:
    """
    Downloads and installs a backend from the provided URL.

    Parameters:
        backend_name: The name of the backend.
        url: The entry point URL.
        version: The specific version of the backend.
        config: configuration for the backend's installation.
        context: The current context.

    Raise:
        [`DownloadBackendFailed`](DownloadBackendFailed): If the download of the backend fails.
    """
    async with context.start(
        action="download_install",
        with_attributes={"backend": backend_name, "version": version},
    ) as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        assets_downloader = await ctx.get("assets_downloader", AssetsDownloader)

        folder = env.pathsBook.local_cdn_component(name=backend_name, version=version)
        if not folder.exists():
            await ctx.send(
                DownloadBackendEvent(
                    name=backend_name, version=version, event="started"
                )
            )
            status = await assets_downloader.wait_asset(
                url=url, kind="package", raw_id=encode_id(backend_name), context=ctx
            )
            if not status.succeeded:
                await ctx.send(
                    DownloadBackendEvent(
                        name=backend_name, version=version, event="failed"
                    )
                )
                raise DownloadBackendFailed(
                    name=backend_name, version=version, context_id=status.context_id
                )

            await ctx.send(
                DownloadBackendEvent(
                    name=backend_name, version=version, event="succeeded"
                )
            )
        folder = env.pathsBook.local_cdn_component(name=backend_name, version=version)
        build_fingerprint = get_build_fingerprint(config)

        if not (folder / install_manifest_name(build_fingerprint)).exists():
            await install_backend_shell(
                folder=folder,
                name=backend_name,
                version=version,
                config=config,
                context=ctx,
            )
