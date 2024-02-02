# standard library
import dataclasses

from asyncio.subprocess import Process

# third parties
import psutil

from pydantic import BaseModel
from semantic_version import Spec, Version

# Youwol utilities
from youwol.utils import Context


class ProxiedBackend(BaseModel):
    """
    Proxy for custom backend description.
    """

    name: str
    """
    Name of the targeted backend.
    """
    version: str
    """
    Version of the targeted backend.
    """
    port: int
    """
    Associated port.
    """
    process: Process | None
    """
    Associated process if the backend has been started through py-youwol.
    """


class ProxyInfo(BaseModel):
    """
    Info regarding a [ProxiedBackend](@yw-nav-class:youwol.app.environment.proxied_backends.ProxiedBackend).
    """

    name: str
    """
    Name of the targeted backend.
    """
    version: str
    """
    Version of the targeted backend.
    """
    port: int
    """
    Associated port.
    """
    pid: int | None
    """
    Process ID of the starting shell command if the backend has been started through py-youwol.
    """
    serverPid: int | None
    """
    Process ID of the server listening on the given port.
    """


@dataclasses.dataclass(frozen=False)
class BackendsStore:
    """
    Stateful list of installed proxies that point to custom backends.
    """

    store: list[ProxiedBackend] = dataclasses.field(default_factory=list)
    """
    The stateful store at a particular point in time.
    """

    def register(
        self, name: str, version: str, port: int, process: Process
    ) -> ProxiedBackend:
        """
        Register a backend to be proxied.

        Parameters:
            name: Name of the backend targeted.
            version:  Version of the backend targeted.
            port: Serving's port.
            process: Associated process that started the backend (if known).

        Return:
            The associated proxy.
        """
        store = self.store
        proxied = ProxiedBackend(name=name, version=version, port=port, process=process)
        store.append(proxied)
        return proxied

    async def terminate(self, name: str, version: str, context: Context) -> None:
        """
        Terminate a backend (if execution owned by youwol) and remove associated proxy.

        Parameters:
            name: Name of the backend targeted.
            version:  Version of the backend targeted.
            context: current context.
        """
        async with context.start("BackendsStore.terminate"):
            proxy = next(
                backend
                for backend in self.store
                if backend.name == name and backend.version == version
            )
            # Process are not killed if it has not been started by py-youwol
            if proxy.process:
                # Getting the process from the listening port is not and ideal solution.
                # The proxy does point to the Process created when starting 'main.py', but this process is not the
                # actual process of the uvicorn server (the actual pid of the uvicorn process is usually
                # `proxy.process.pid + 1`).
                # Not sure about the best option to deal with that issue. For now, we use the serving port to retrieve
                # the actual PID of the backend's server.
                pid_from_port = BackendsStore.get_pid_using_port(proxy.port)
                psutil.Process(pid_from_port).terminate()

            self.store = [backend for backend in self.store if backend != proxy]

    def get_info(self, name: str, query_version: str) -> ProxyInfo | None:
        """
        Return the info regarding a proxy from a backend name and semver query.

        Parameters:
            name: Name of the proxied backend targeted.
            query_version: Semantic versioning query

        Return:
            The info if found, None otherwise.
        """
        proxy = self.get(name=name, query_version=query_version)
        if not proxy:
            return None
        pid_from_port = BackendsStore.get_pid_using_port(proxy.port)
        return ProxyInfo(
            name=name,
            version=proxy.version,
            port=proxy.port,
            pid=proxy.process and proxy.process.pid,
            serverPid=pid_from_port,
        )

    def get(self, name: str, query_version: str) -> ProxiedBackend | None:
        """
        Return the latest version of the proxied backend from the store that match the given name and
        semantic versioning query.

        Parameters:
            name: Name of the proxied backend targeted.
            query_version: Semantic versioning query

        Return:
            The matching element if found, None otherwise.
        """

        store = self.store
        query_spec = Spec(query_version)

        matching_versions = [
            backend
            for backend in store
            if backend.name == name and query_spec.match(Version(backend.version))
        ]

        if not matching_versions:
            return None

        latest_version_backend = sorted(
            matching_versions, key=lambda x: Version(x.version), reverse=True
        )[0]

        return latest_version_backend

    @staticmethod
    def get_pid_using_port(port):
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return conn.pid
        return None