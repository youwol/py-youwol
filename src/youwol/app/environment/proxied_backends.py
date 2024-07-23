# standard library
import dataclasses
import subprocess
import time
import uuid

from asyncio.subprocess import Process

# third parties
import psutil

from psutil import AccessDenied
from pydantic import BaseModel
from semantic_version import Spec, Version

# Youwol utilities
from youwol.utils import Context, json2uid

DEFAULT_PARTITION_ID = "Default"


class ProxiedBackendConfiguration(BaseModel):
    """
    Represents the configuration of a proxied backend.
    """

    build: dict[str, str] = {}
    """
    Configuration elements regarding build time.
    """


class ProxiedBackend(BaseModel):
    """
    Proxy for custom backend description.
    """

    partition_id: str
    """
    Encapsulating partition.
    """
    name: str
    """
    Name of the targeted backend.
    """
    version: str
    """
    Version of the targeted backend.
    """
    configuration: ProxiedBackendConfiguration
    """
    Configuration, if any, of the backend.
    """
    uid: str
    """
    Uid that uniquely identifies name + version + configuration.
    """
    port: int
    """
    Associated port.
    """
    process: Process | None
    """
    Associated process if the backend has been started through py-youwol.
    """
    started_at: float
    """
    Starting time in Epoch (second).
    """
    endpoint_ctx_id: list[str] = []
    """
    Context UIDs including the direct call to the backend's endpoint.
    """
    server_outputs_ctx_id: str | None = None
    """
    Context UID including the print statements in std output of the backend.
    """
    install_outputs: list[str] | None
    """
    Outputs generated by the `install.sh` script.
    """


class ProxyInfo(BaseModel):
    """
    Serialization of a :class:`ProxiedBackend <youwol.app.environment.proxied_backends.ProxiedBackend>`.
    """

    uid: str
    """
    Unique identifier among backends.
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
    startedAt: float
    """
    Starting time in Epoch (second).
    """
    partitionId: str
    """
    Encapsulating partition.
    """
    configuration: ProxiedBackendConfiguration
    """
    Configuration of the backend.
    """


def get_build_fingerprint(config: ProxiedBackendConfiguration) -> str:
    return json2uid(config.build)


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
        self,
        partition_id: str,
        name: str,
        version: str,
        configuration: ProxiedBackendConfiguration,
        port: int,
        process: Process,
        install_outputs: list[str] | None = None,
        server_outputs_ctx_id: str | None = None,
    ) -> ProxiedBackend:
        """
        Register a backend to be proxied.

        Parameters:
            partition_id: Encapsulating partition.
            name: Name of the backend targeted.
            version:  Version of the backend targeted.
            configuration: Configuration of the backend, if any.
            port: Serving's port.
            process: Associated process that started the backend (if known).
            install_outputs: Outputs generated by the `install.sh` script.
            server_outputs_ctx_id: Parent context's ID for servers std outputs
        Return:
            The associated proxy.
        """
        store = self.store
        proxied = ProxiedBackend(
            partition_id=partition_id,
            name=name,
            version=version,
            configuration=configuration,
            uid=str(uuid.uuid4()),
            started_at=time.time(),
            port=port,
            process=process,
            install_outputs=install_outputs,
            server_outputs_ctx_id=server_outputs_ctx_id,
        )
        store.append(proxied)
        return proxied

    async def terminate(self, uid: str, context: Context) -> None:
        """
        Terminate a backend (if execution owned by youwol) and remove associated proxy.

        Parameters:
            uid: Backend's UID.
            context: current context.
        """
        async with context.start("BackendsStore.terminate"):
            proxy = next(backend for backend in self.store if backend.uid == uid)
            # Process are not killed if it has not been started by py-youwol
            if proxy.process:
                # Getting the process from the listening port is not and ideal solution.
                # The proxy does point to the Process created when starting 'main.py', but this process is not the
                # actual process of the uvicorn server (the actual pid of the uvicorn process is usually
                # `proxy.process.pid + 1`).
                # Not sure about the best option to deal with that issue. For now, we use the serving port to retrieve
                # the actual PID of the backend's server.
                pid_from_port = BackendsStore.get_pid_using_port(proxy.port)
                if pid_from_port:
                    psutil.Process(pid_from_port).terminate()

            self.store = [backend for backend in self.store if backend != proxy]

    def get(self, uid: str) -> ProxyInfo | None:
        return next((p for p in self.store if p.uid == uid), None)

    def get_info(
        self, partition_id: str, name: str, query_version: str
    ) -> ProxyInfo | None:
        """
        Return the info regarding a proxy from a backend name and semver query.

        Parameters:
            partition_id: Encapsulating partition.
            name: Name of the proxied backend targeted.
            query_version: Semantic versioning query.

        Return:
            The info if found, None otherwise.
        """
        proxy = self.query_latest(
            partition_id=partition_id, name=name, query_version=query_version
        )
        if not proxy:
            return None
        pid_from_port = BackendsStore.get_pid_using_port(proxy.port)
        return ProxyInfo(
            name=name,
            uid=proxy.uid,
            version=proxy.version,
            port=proxy.port,
            pid=proxy.process and proxy.process.pid,
            startedAt=proxy.started_at,
            serverPid=pid_from_port,
            partitionId=proxy.partition_id,
            configuration=proxy.configuration,
        )

    def query_latest(
        self, partition_id: str | None, name: str, query_version: str
    ) -> ProxiedBackend | None:
        """
        Return the latest version of the proxied backend from the store matching the given name and
        semantic versioning query.

        Parameters:
            name: Name of the proxied backend targeted.
            query_version: Semantic versioning query
            partition_id: Encapsulating partition, `None` allowed only for backward compatibility.

        Return:
            The matching element if found, None otherwise.
        """

        store = self.store
        query_spec = Spec(query_version)

        matching_versions = [
            backend
            for backend in store
            if backend.name == name
            and (backend.partition_id == partition_id if partition_id else True)
            and query_spec.match(Version(backend.version))
        ]

        if not matching_versions:
            return None

        latest_version_backend = sorted(
            matching_versions, key=lambda x: Version(x.version), reverse=True
        )[0]

        return latest_version_backend

    @staticmethod
    def get_pid_using_port(port):
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return conn.pid
        except AccessDenied:
            # On e.g. macOS `psutil.net_connections()` can not be called without elevated privileges,
            # fallback using 'lsof' in this case.
            output = subprocess.check_output(["lsof", "-i", f"tcp:{port}", "-t"])
            return int(output.decode().strip())

        return None
