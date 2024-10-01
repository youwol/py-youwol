# standard library
import asyncio
import functools
import subprocess
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
    StartCommand,
    Trigger,
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
    """
    Represents errors occurring while installing a backend using execution of a shell command.
    """

    def __init__(self, return_code: int, outputs: list[str], ctx_id: str):
        """
        Initializes the instance.

        Parameters:
            return_code: Return code when the `install` command has been executed.
            outputs: Command's outputs.
            ctx_id: Failing execution context ID.
        """
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
    """
    Represents errors occurring while starting a backend using execution of a shell command.
    """

    def __init__(self, return_code: int, outputs: list[str], ctx_id: str):
        """
        Initializes the instance.

        Parameters:
            return_code: Return code when the `install` command has been executed.
            outputs: Command's outputs.
            ctx_id: Failing execution context ID.
        """
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
    """
    Represents errors occurring while starting a backend using a shell command and a time-out is reached.
    """

    def __init__(self, outputs: list[str], ctx_id: str):
        """
        Initializes the instance.

        Parameters:
            outputs: Command's outputs.
            ctx_id: Failing execution context ID.
        """
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


async def get_install_cmd(
    folder: Path,
    name: str,
    version: str,
    config: ProxiedBackendConfiguration,
    context: Context,
) -> str:
    """
    Generate the command to install a backend service, either using `Docker` or a local shell script.

    This function checks the existence of `Dockerfile` and `install.sh` in the provided folder and generates
    the appropriate installation command based on the available method (Docker or shell script). If `Docker` and
    `Dockerfile` are available, it constructs a Docker build command; otherwise, it falls back to the shell script
    if present.

    Parameters:
        folder: The directory containing the backend service's installation files (`Dockerfile` or `install.sh`).
        name: The name of the backend service to be installed.
        version: The version of the backend service.
        config: Configuration object containing build parameters for the backend service.
        context: The execution context used for logging, event tracking, and retrieving environment details.

    Returns:
        str: The generated command to install the backend service.

    Raises:
        RuntimeError: If neither `Dockerfile` nor `install.sh` is found in the specified folder, or if only
            `Dockerfile` is found but `docker` is not available on the host.
    """

    async with context.start(
        action="get_install_cmd",
        with_reporters=[LogsStreamer()],
    ) as ctx:

        install_sh = folder / "install.sh"
        dockerfile = folder / "Dockerfile"
        build_fingerprint = get_build_fingerprint(
            name=name, version=version, config=config
        )

        if dockerfile.exists() and is_docker_available():
            build_args = functools.reduce(
                lambda acc, e: f'{acc} --build-arg {e[0]}="{e[1]}"',
                config.build.items(),
                "",
            )
            cmd = f"docker build {build_args} -t {name}:{version} -t {name}:{build_fingerprint} -t {name}:youwol ."
            await ctx.info(f"Install containerized backend: '{cmd}'")
            return cmd

        if install_sh.exists():
            if dockerfile.exists():
                await ctx.warning(
                    text="Docker is not available on host, fallback to 'install.sh' to install service."
                )

            build_args = functools.reduce(
                lambda acc, e: f"{acc} --{e[0]} '{e[1]}'",
                config.build.items(),
                f"--fingerprint {build_fingerprint}",
            )
            cmd = f"sh ./install.sh {build_args}"
            await ctx.info(f"Install localhost backend: '{cmd}'")
            return cmd

        if not dockerfile.exists() and not install_sh.exists():
            raise RuntimeError(
                "Can not install service as neither 'Dockerfile' nor 'start.sh' are found"
            )

        if dockerfile.exists():
            raise RuntimeError(
                "Only docker based backend setup is available, but Docker is not available on host."
            )


async def install_backend_shell(
    folder: Path,
    name: str,
    version: str,
    config: ProxiedBackendConfiguration,
    context: Context,
) -> list[str]:
    """
    Installs a backend service by running a shell command (either Docker-based or shell-script based).

    This function initiates the installation process for a backend service. It first generates an installation command
    using :func:`youwol.app.routers.backends.implementation.get_install_cmd`, then executes the command in the
    provided folder.
    The installation process is tracked within the provided `context`, including logging, event sending,
    and error handling.

    Parameters:
        folder: The directory containing the backend's installation files (`Dockerfile` or `install.sh`).
        name: The name of the backend service to be installed.
        version: The version of the backend service.
        config: Configuration object containing build parameters and options for
            the backend service.
        context: The execution context used for logging, event tracking, and retrieving environment details.

    Returns:
        A list of output strings from the shell command executed during the installation.

    Raises:
        InstallBackendFailed: If the installation process fails (i.e., if the shell command returns a non-zero code).
    """
    install_id = str(uuid.uuid4())

    async with context.start(
        action="install backend",
        with_labels=[Label.INSTALL_BACKEND_SH],
        with_attributes={"name": name, "version": version, "installId": install_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        build_fingerprint = get_build_fingerprint(
            name=name, version=version, config=config
        )
        await ctx.send(
            InstallBackendEvent(
                name=name, version=version, event="started", installId=install_id
            )
        )
        cmd_install = await get_install_cmd(
            folder=folder, name=name, version=version, config=config, context=ctx
        )
        return_code, outputs = await execute_shell_cmd(
            cmd=cmd_install, cwd=folder, context=ctx
        )
        if return_code > 1:
            await ctx.send(
                InstallBackendEvent(
                    name=name, version=version, event="failed", installId=install_id
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
                name=name, version=version, event="succeeded", installId=install_id
            )
        )
        return outputs


async def get_start_command(
    name: str,
    version: str,
    config: ProxiedBackendConfiguration,
    instance_id: str,
    folder: Path,
    port: int,
    context: Context,
) -> StartCommand:
    """
    Generates the appropriate command to start a backend service, either in a Docker container or locally via a
    shell script.

    The function determines whether the backend service should be started within a Docker container or using a local
    shell script (`start.sh`). Based on the available files in the given folder (either a `Dockerfile` or `start.sh`),
    and the availability of  ̀docker`, the function returns the necessary start command for the backend.

    Parameters:
        name: The name of the backend service to start.
        version: The version of the backend service.
        config: Configuration object containing the backend's build parameters and environment settings.
        instance_id: Unique identifier for the backend instance to be started.
        folder: Directory containing the backend's files (`Dockerfile` or `start.sh`).
        port: The port on which the backend service should be exposed.
        context: The execution context used for logging, event tracking, and retrieving environment details.

    Returns:
        The starting command description.

    Raises:
        RuntimeError: If neither a `Dockerfile` nor a `start.sh` script is found in the specified folder,
            or if a `Dockerfile` exists, not the `start.sh` script, and Docker is not available on the host.

    Notes:
        - When running within a Docker container, the backend will communicate with the host through the `YW_HOST`
          environment variable, which is set to `host.docker.internal`.
    """
    async with context.start(action="get_start_command") as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        fp = get_build_fingerprint(name=name, version=version, config=config)
        dockerfile = folder / "Dockerfile"
        start_sh = folder / "start.sh"
        if dockerfile.exists() and is_docker_available():
            await ctx.info("Backend started within container")
            yw_host = "host.docker.internal"
            return StartCommand(
                runningMode="container",
                cmd=(
                    f"docker run --add-host {yw_host}=host-gateway --name {instance_id} "
                    f"--env YW_HOST={yw_host} --env YW_PORT={env.httpPort} -p {port}:8080 {name}:{fp} --rm"
                ),
                cwd=folder,
            )
        if start_sh.exists():
            if dockerfile.exists():
                await ctx.warning(
                    text="Docker is not available on host, fallback to 'start.sh' to start service."
                )
            await ctx.info("Backend started within host")
            build_arg = f" -b {fp}"
            return StartCommand(
                runningMode="localhost",
                cmd=(
                    f"(cd {folder} &&  sh ./start.sh -p {port} -s {env.httpPort} {build_arg})"
                ),
                cwd=folder,
            )

        if not dockerfile.exists() and not start_sh.exists():
            raise RuntimeError(
                "Can not start service as neither 'Dockerfile' nor 'start.sh' are found"
            )

        if dockerfile.exists():
            raise RuntimeError(
                "Only docker based backend setup is available, but Docker is not available on host."
            )


async def start_backend_shell(
    name: str,
    version: str,
    config: ProxiedBackendConfiguration,
    instance_id: str,
    folder: Path,
    port: int,
    outputs: list[str],
    context: Context,
) -> tuple[StartCommand, Process, str]:
    """
    Starts a backend service by executing either a `Docker` command or a shell script,
    depending on the configuration and environment.

    This function orchestrates the starting process of a backend service by:
    1. Retrieving the appropriate :func:`start command<youwol.app.routers.backends.implementation.get_start_command>`.
    2. Running the command as a subprocess.
    3. Collecting and streaming the subprocess output in real-time.

    Parameters:
        name: The name of the backend service to start.
        version: The version of the backend service.
        config: Configuration object containing the backend's environment and build settings.
        instance_id: Unique identifier for the backend instance.
        folder: The directory where the command is executed.
        port: The port to expose the backend service.
        outputs: A list that will be populated with the backend's output logs (stdout and stderr).
        context: The execution context used for logging, event tracking, and other runtime information.

    Returns:
        A tuple containing:
            - **StartCommand**: Description of the command used to start the backend.
            - **Process**: The subprocess object representing the running backend service.
            - **str**: The unique context ID (`ctx.uid`) for tracking the execution.
    """
    async with context.start(
        action="start backend",
        with_labels=[Label.START_BACKEND_SH],
        with_attributes={"name": name, "version": version},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        cmd_start = await get_start_command(
            name=name,
            version=version,
            config=config,
            instance_id=instance_id,
            folder=folder,
            port=port,
            context=ctx,
        )

        await ctx.info(text=cmd_start.cmd)
        p = await asyncio.create_subprocess_shell(
            cmd=cmd_start.cmd,
            cwd=cmd_start.cwd,
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
        return cmd_start, p, ctx.uid


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
    Ensure a backend is running, eventually
    :func:`installing<youwol.app.routers.backends.implementation.install_backend_shell>` and
    :func:`starting<youwol.app.routers.backends.implementation.start_backend_shell>` it.

    Parameters:
        request: Incoming request.
        partition_id: Expected partition ID.
        backend_name: Backend's name.
        version_query: Semver query for the backend's version.
        config: Expected backend's configuration. None` means: take corresponding service if running whatever
            its configuration.
        timeout: Timeout for the all process.
        context: The execution context used for logging, event tracking, and retrieving environment details.

    Returns:
        Proxied backend information.

    Raises:
        HTTPException: Not matching version for the requested backend exists.
        StartBackendCrashed: The backend's starting command returned with error.
        StartBackendTimeout: The provided timeout has been reached before the backend was able to respond.
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
        fp = get_build_fingerprint(
            name=backend_name, version=latest_version_backend, config=config
        )

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

        instance_id = str(uuid.uuid4())
        await ctx.info(
            text=f"Start backend from '{folder}' on port {port} with ID {instance_id}"
        )

        outputs = []
        await ctx.send(
            data=StartBackendEvent(
                uid=instance_id,
                partitionId=partition_id,
                name=backend_name,
                version=latest_version_backend,
                event="starting",
            )
        )
        start_cmd, process, std_outputs_ctx_id = await start_backend_shell(
            name=backend_name,
            version=latest_version_backend,
            instance_id=instance_id,
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
            # If the backend is running in a container, there is no 'owning process'
            # Btw, in macOS, the process here when doing 'docker run ...' is the docker desktop process.
            owned_process = process if start_cmd.runningMode == "localhost" else None
            proxy = env.proxied_backends.register(
                uid=instance_id,
                partition_id=partition_id,
                name=backend_name,
                version=latest_version_backend,
                configuration=config,
                port=port,
                trigger=Trigger(cmd=start_cmd, process=owned_process),
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
            if owned_process:
                owned_process.terminate()
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

    Raises:
        DownloadBackendFailed: If the download of the backend fails.
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
        build_fingerprint = get_build_fingerprint(
            name=backend_name, version=version, config=config
        )

        if not (folder / install_manifest_name(build_fingerprint)).exists():
            await install_backend_shell(
                folder=folder,
                name=backend_name,
                version=version,
                config=config,
                context=ctx,
            )


def is_docker_available():
    try:
        subprocess.run(["docker", "--version"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False
