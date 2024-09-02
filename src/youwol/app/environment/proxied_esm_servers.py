# standard library
import asyncio
import dataclasses
import subprocess

from asyncio.subprocess import Process
from collections.abc import Awaitable, Callable

# third parties
import psutil

from psutil import AccessDenied
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import Context, Label


class ProxiedEsmServerInfo(BaseModel):
    """
    Response model proxy for ESM servers (e.g. dev-server).
    """

    uid: str
    """
    Proxy unique identifier.
    """
    package: str
    """
    Name of the targeted ESM package.
    """
    version: str
    """
    Version of the targeted ESM package.
    """
    port: int
    """
    Associated port.
    """
    pid: int | None
    """
    Process ID of the starting shell command if the server has been started through py-youwol.
    """
    serverPid: int | None
    """
    Process ID of the server listening on the given port.
    """


@dataclasses.dataclass(frozen=True)
class EsmServerDispatchInput:
    package: str
    version: str
    port: int
    target: list[str]
    request: Request


class ProxiedEsmServer(BaseModel):
    """
    Proxy for ESM live servers (dev-server).
    """

    uid: str
    """
    Proxy unique identifier.
    """
    package: str
    """
    Name of the targeted ESM package.
    """
    version: str
    """
    Version of the targeted ESM package.
    """
    port: int
    """
    Associated port.
    """
    process: Process | None
    """
    Associated process if the server has been started through py-youwol.
    """
    dispatch: Callable[[EsmServerDispatchInput, Context], Awaitable[Response | None]]
    """
    The dispatch implementation.
    """

    def info(self):
        """
        Retrieves serializable info.
        """
        return ProxiedEsmServerInfo(
            uid=self.uid,
            package=self.package,
            version=self.version,
            port=self.port,
            pid=self.process and self.process.pid,
            serverPid=self.process and self.get_pid_using_port(self.port),
        )

    async def apply(
        self, request: Request, target: list[str], context: Context
    ) -> Response:
        """
        Apply the dispatch to the ESM server.

        Parameters:
            request: Incoming request.
            target: Targeted path.
            context: Current context.

        Returns:
            The response.
        """
        async with context.start(
            f'Proxy \'/{"/".join(target)}\'',
            with_labels=[Label.DISPATCH_ESM_SERVER],
            with_attributes={
                "proxyUid": self.uid,
                "package": self.package,
                "version": self.version,
            },
            with_reporters=[LogsStreamer()],
        ) as ctx:
            dispatch_input = EsmServerDispatchInput(
                package=self.package,
                version=self.version,
                port=self.port,
                target=target,
                request=request,
            )
            return await self.dispatch(dispatch_input, ctx)

    @staticmethod
    def get_pid_using_port(port):
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return conn.pid
        except AccessDenied:
            # On e.g. macOS `psutil.net_connections()` can not be called without elevated privileges,
            # fallback using 'lsof' in this case.
            try:
                output = subprocess.check_output(["lsof", "-i", f"tcp:{port}", "-t"])
                return int(output.decode().strip())
            except subprocess.CalledProcessError:
                # No process found
                pass

        return None


@dataclasses.dataclass(frozen=False)
class EsmServersStore:
    """
    Stateful list of installed proxies that point to ESM severs.
    """

    store: list[ProxiedEsmServer] = dataclasses.field(default_factory=list)
    """
    The stateful store at a particular point in time.
    """

    async def register(
        self,
        uid: str,
        package: str,
        version: str,
        port: int,
        process: Process,
        dispatch: Callable[
            [EsmServerDispatchInput, Context], Awaitable[Response | None]
        ],
        wait_timeout: float = 0,
    ) -> ProxiedEsmServer:
        """
        Register an ESM server to be proxied within py-youwol.

        Parameters:
            uid: Proxy's UID.
            package: Name of the ESM package targeted.
            version: Version of the ESM module targeted.
            port: Serving's port.
            process: Associated process that started the server (if known).
            dispatch: Function to dispatch the incoming request to the proxied server.
            wait_timeout: If > 0, wait for the PID on the server listening on the given port, try every half a second
            until the PID is retrieved or this timeout is reached.
            The timeout should be a multiple of 0.5s.
            If 0, proceed directly.
        Return:
            The associated proxy.
        """
        store = self.store
        proxied = ProxiedEsmServer(
            uid=uid,
            package=package,
            version=version,
            port=port,
            process=process,
            dispatch=dispatch,
        )
        if not wait_timeout:
            store.append(proxied)
            return proxied

        pid = None
        for _ in range(int(wait_timeout * 2)):
            pid = ProxiedEsmServer.get_pid_using_port(port=port)
            if pid:
                break
            await asyncio.sleep(0.5)
        if not pid:
            raise RuntimeError(
                f"The ESM proxied server for {package} on port {port} did not respond its PID."
            )
        store.append(proxied)
        return proxied

    async def terminate(self, uid: str, context: Context) -> None:
        """
        Terminate a server (if execution owned by youwol) and remove associated proxy.

        Parameters:
            uid: Proxy unique identifier.
            context: current context.
        """
        async with context.start("EsmServersStore.terminate"):

            proxy = next(s for s in self.store if s.uid == uid)

            # Process are not killed if it has not been started by py-youwol
            if proxy.process:
                # Getting the process from the listening port is not and ideal solution.
                # The proxy does point to the Process created when starting 'main.py', but this process is not the
                # actual process of the uvicorn server (the actual pid of the uvicorn process is usually
                # `proxy.process.pid + 1`).
                # Not sure about the best option to deal with that issue. For now, we use the serving port to retrieve
                # the actual PID of the server.
                pid_from_port = proxy.info().serverPid
                if pid_from_port:
                    psutil.Process(pid_from_port).terminate()

            self.store = [server for server in self.store if server != proxy]

    def get(self, package: str, version: str) -> ProxiedEsmServer | None:
        """
        Return the info regarding a proxy from name & version.

        Parameters:
            package: Name of the proxied ESM module targeted.
            version: Version of the ESM module targeted.
        Return:
            The info if found, None otherwise.
        """
        return next(
            (s for s in self.store if s.package == package and s.version == version),
            None,
        )
