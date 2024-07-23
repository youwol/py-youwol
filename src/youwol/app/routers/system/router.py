# standard library
import asyncio
import os
import time

from pathlib import Path

# typing
from typing import cast

# third parties
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment, yw_config
from youwol.app.environment.proxied_backends import ProxiedBackendConfiguration
from youwol.app.routers.backends.implementation import (
    INSTALL_MANIFEST_FILE,
    download_install_backend,
    ensure_running,
)
from youwol.app.routers.environment.router import emit_environment_status
from youwol.app.routers.system.models import (
    BackendInstallResponse,
    BackendLogsResponse,
    BackendsGraphInstallResponse,
    FolderContentBody,
    FolderContentResp,
    LeafLogResponse,
    Log,
    LogsResponse,
    NodeLogResponse,
    NodeLogsResponse,
    NodeLogStatus,
    PostDataBody,
    PostLogsBody,
    TerminateResponse,
    UninstallResponse,
)

# Youwol utilities
from youwol.utils.context import Context, InMemoryReporter, Label, LogEntry, LogLevel
from youwol.utils.http_clients.cdn_backend import LoadingGraphResponseV1

router = APIRouter()


@router.get("/file/{rest_of_path:path}", summary="return file content")
async def get_file(rest_of_path: str) -> FileResponse:
    """
    Get a file content on disk.

    Parameters:
        rest_of_path: the path of the file.

    Return:
        The file content.
    """
    return FileResponse(rest_of_path)


@router.post(
    "/folder-content",
    response_model=FolderContentResp,
    summary="return the items in target folder",
)
async def folder_content(body: FolderContentBody) -> FolderContentResp:
    """
    Query a folder content on disk.

    Parameters:
        body: target folder.

    Return:
        The content of the folder.
    """
    path = Path(body.path)
    if not path.is_dir():
        return FolderContentResp(files=[], folders=[])
    # if 'List[str]' not provided => items result in 'Union[List[str], List[bytes]]'...?
    items: list[str] = os.listdir(path)
    return FolderContentResp(
        files=[item for item in items if os.path.isfile(path / item)],
        folders=[item for item in items if os.path.isdir(path / item)],
    )


class BackendsGraphInstallBody(LoadingGraphResponseV1):
    """
    Represents the body of the endpoint `/backends/install`.
    """

    partitionId: str

    backendsConfig: dict[str, ProxiedBackendConfiguration] = {}
    """
    Configurations that will be forwarded to backends during installation.

    **Keys** are backend name with optional semantic versioning to select the actual backends within the installation
    for which the configuration apply to. E.g. `foo-backend` (target any version of `foo-backend`) or
    `foo-backend#^1.0.0` (target any version of `foo-backend` compatible with `^1.0.0`).
    """


@router.post(
    "/backends/install",
    response_model=BackendsGraphInstallResponse,
    summary="Install the backends part of a loading graph from a cdn-backend response.",
)
async def install_graph(
    request: Request, body: BackendsGraphInstallBody
) -> BackendsGraphInstallResponse:
    """
    This function processes the backend part of a loading graph's definition to install and ensure the running state
    of each backend component defined within.
    It respects the hierarchical structure of the loading graph, ensuring that each layer of dependencies is correctly
    installed and started in sequence.
    Operations on backends within the same layer are performed concurrently, for efficient parallel execution.

    Some comments regarding configuration

    Note:
        Loading graph definitions are retrieved using this
        :func:`endpoint <youwol.backends.cdn.root_paths.resolve_loading_tree>` of
        the :mod:`cdn-backend <youwol.backends.cdn>` service.

    Parameters:
        request: Incoming request.
        body: An object containing the lock and definition of the loading graph, which specifies the backend components
         to be installed and their dependencies.

    Return:
        Description of the backends installed, including their client bundle.

    Raise:
    - Potential exceptions from download_install_backend and ensure_running functions, including network errors,
      installation failures, and timeouts in starting backends.
    """

    async with Context.start_ep(
        request=request,
    ) as ctx:
        default_config = ProxiedBackendConfiguration()
        backends_dict = {
            entity.id: entity for entity in body.lock if entity.type == "backend"
        }
        sub_graph = [
            [
                (backends_dict[backend[0]], f"/backends/{backend[1]}")
                for backend in layer
                if backend[0] in backends_dict
            ]
            for layer in body.definition
        ]
        sub_graph = [graph for graph in sub_graph if len(graph) > 0]
        flat = [d for layer in sub_graph for d in layer]

        await asyncio.gather(
            *[
                download_install_backend(
                    backend_name=backend.name,
                    version=backend.version,
                    config=body.backendsConfig.get(backend.name, default_config),
                    url=url,
                    context=ctx,
                )
                for backend, url in flat
            ]
        )
        for layer in sub_graph:
            await asyncio.gather(
                *[
                    ensure_running(
                        request=ctx.request,
                        partition_id=body.partitionId,
                        backend_name=lib.name,
                        version_query=lib.version,
                        config=body.backendsConfig.get(lib.name, default_config),
                        timeout=300,
                        context=ctx,
                    )
                    for lib, _ in layer
                ]
            )

        return BackendsGraphInstallResponse(
            backends=[
                BackendInstallResponse.from_lib_info(
                    backend=backend,
                    partition=body.partitionId,
                    config=body.backendsConfig.get(backend.name, default_config),
                )
                for backend in backends_dict.values()
            ]
        )


@router.delete(
    "/backends/{uid}/terminate",
    summary="Terminate a backend",
    response_model=TerminateResponse,
)
async def terminate(
    request: Request,
    uid: str,
    env: YouwolEnvironment = Depends(yw_config),
):
    """
    Terminate a backend.

    Parameters:
        request: Incoming request.
        uid: Backend or partition UID
        env: Injected current YouwolEnvironment.
    Return:
        Termination details.
    """
    async with Context.start_ep(
        request=request,
    ) as ctx:
        proxieds = [
            b for b in env.proxied_backends.store if uid in (b.partition_id, b.uid)
        ]
        if proxieds:
            await asyncio.gather(
                *[
                    env.proxied_backends.terminate(uid=b.uid, context=ctx)
                    for b in proxieds
                ]
            )
            await emit_environment_status(context=ctx)
            return TerminateResponse(uids=[b.uid for b in proxieds])
        raise HTTPException(
            status_code=400, detail="Backend or partition UID not found"
        )


@router.delete(
    "/backends/{name}/{version}/terminate",
    summary="Terminate a backend",
    response_model=TerminateResponse,
)
async def terminate_deprecated(
    request: Request,
    name: str,
    version: str,
    env: YouwolEnvironment = Depends(yw_config),
):
    """
    Deprecated, use `/backends/{uid}/terminate` instead.
    """
    proxied = env.proxied_backends.query_latest(
        partition_id=None, name=name, query_version=version
    )
    return await terminate(request=request, uid=proxied.uid, env=env)


@router.delete(
    "/backends/{name}/{version}/uninstall",
    summary="Uninstall a backend",
    response_model=UninstallResponse,
)
async def uninstall(
    request: Request,
    name: str,
    version: str,
    env: YouwolEnvironment = Depends(yw_config),
):
    """
    Uninstall a backend, eventually terminate associated running instances.

    Parameters:
        request: incoming request.
        name: Name if the backend.
        version: Version of the backend.
        env: Injected current YouwolEnvironment.
    Return:
        Uninstallation details.
    """
    async with Context.start_ep(
        request=request,
    ) as ctx:
        proxied_backends = env.proxied_backends
        running = [
            p for p in proxied_backends.store if p.name == name and p.version == version
        ]
        if running:
            await asyncio.gather(
                *[proxied_backends.terminate(uid=p.uid, context=ctx) for p in running]
            )
            await emit_environment_status(context=ctx)

        folder = env.pathsBook.local_cdn_component(name=name, version=version)
        manifest_removed = False
        for file_path in folder.glob(INSTALL_MANIFEST_FILE.replace(".txt", ".*")):
            file_path.unlink()
            manifest_removed = True

        return UninstallResponse(
            name=name,
            version=version,
            backendTerminated=len(running) > 0,
            wasInstalled=manifest_removed,
        )


@router.get("/backends/{name}/{version}/logs/", summary="Query in-memory root logs.")
async def query_backend_logs(
    request: Request,
    name: str,
    version: str,
    env: YouwolEnvironment = Depends(yw_config),
) -> BackendLogsResponse:
    """
    Query in-memory logs for a given backend at given version, returned ordered w/ last emitted first.

    Parameters:
        request: incoming request
        name: Name if the backend
        version: Version of the backend
        env: Injected current YouwolEnvironment
    Return:
        logs list.
    """
    async with Context.start_ep(
        request=request,
    ):
        logs: list[Log] = []
        proxy = env.proxied_backends.query_latest(
            name=name, query_version=version, partition_id=None
        )
        if not proxy:
            raise HTTPException(
                status_code=404,
                detail=f"Backend {name} at version {version} not included in proxies.",
            )
        for ctx_id in proxy.endpoint_ctx_id:
            inner_logs = await get_logs(request=request, parent_id=ctx_id)
            logs.extend(
                [log for log in inner_logs.logs if str(Label.STARTED) in log.labels]
            )

        std_outputs = await get_logs(
            request=request, parent_id=proxy.server_outputs_ctx_id
        )

        return BackendLogsResponse(
            logs=sorted(logs, key=lambda n: n.timestamp),
            server_outputs=[log.text for log in std_outputs.logs],
            install_outputs=proxy.install_outputs,
        )


@router.get("/logs/", summary="Query in-memory root logs.")
async def query_logs(
    request: Request,
    from_timestamp: int = Query(alias="from-timestamp", default=time.time()),
    max_count: int = Query(alias="max-count", default=1000),
) -> NodeLogsResponse:
    """
    Query in-memory root logs, returned ordered w/ last emitted first.

    Parameters:
        request: incoming request
        from_timestamp: return only logs emitted after this timestamp (time since epoch in seconds)
        max_count: maximum number of root logs returned

    Return:
        logs list.
    """

    response: NodeLogsResponse | None = None
    async with Context.start_ep(
        with_attributes={"fromTimestamp": from_timestamp, "maxCount": max_count},
        response=lambda: response,
        request=request,
    ) as ctx:
        logger = cast(InMemoryReporter, ctx.logs_reporters[0])
        logs = []
        for log in reversed(logger.root_node_logs):
            failed = log.context_id in logger.errors
            unresolved = log.context_id in logger.futures
            logs.append(
                NodeLogResponse(
                    **Log.from_log_entry(log).dict(),
                    failed=failed,
                    future=unresolved,
                    status=get_status(log, logger),
                )
            )
            if len(logs) > max_count:
                break
        response = NodeLogsResponse(logs=logs)
        return response


@router.get("/logs/{parent_id}", summary="Query all logs with given parent ID")
async def get_logs(request: Request, parent_id: str) -> LogsResponse:
    """
    Query all logs with given parent ID.

    Parameters:
        request: incoming request
        parent_id: parent ID requested

    Return:
        The list of logs.
    """

    async with Context.start_ep(request=request) as ctx:
        logger = cast(InMemoryReporter, ctx.logs_reporters[0])
        nodes_logs, leaf_logs, errors, futures = (
            logger.node_logs,
            logger.leaf_logs,
            logger.errors,
            logger.futures,
        )

        nodes: list[Log] = [
            NodeLogResponse(
                **Log.from_log_entry(log).dict(),
                failed=log.context_id in errors,
                future=log.context_id in futures,
                status=get_status(log, logger),
            )
            for log in nodes_logs
            if log.parent_context_id == parent_id
        ]
        leafs: list[Log] = [
            LeafLogResponse(**Log.from_log_entry(log).dict())
            for log in leaf_logs
            if log.context_id == parent_id
        ]

        return LogsResponse(logs=sorted(nodes + leafs, key=lambda n: n.timestamp))


@router.post("/logs", summary="post logs")
async def post_logs(request: Request, body: PostLogsBody):
    """
    Forward log entries to the :attr:`Context.logs_reporters <youwol.utils.context.context.Context.logs_reporters>`.

    Parameters:
        request: Incoming request.
        body: The logs to add.
    """
    context = Context.from_request(request=request)
    for log in body.logs:
        entry = LogEntry(
            level=LogLevel.INFO,
            text=log.text,
            data=log.data,
            labels=log.labels,
            attributes=log.attributes,
            context_id=log.contextId,
            parent_context_id=log.parentContextId,
            trace_uid=log.traceUid,
            timestamp=log.timestamp,
        )
        for logger in context.logs_reporters:
            await logger.log(entry=entry)


@router.post("/data", summary="post data")
async def post_data(request: Request, body: PostDataBody):
    """
    Forward data entries to the :attr:`Context.data_reporters <youwol.utils.context.context.Context.data_reporters>`.

    Parameters:
        request: Incoming request.
        body: The data to send.

    """
    context = Context.from_request(request=request)
    for log in body.data:
        entry = LogEntry(
            level=LogLevel.INFO,
            text=log.text,
            data=log.data,
            labels=log.labels,
            attributes=log.attributes,
            context_id=log.contextId,
            parent_context_id=log.parentContextId,
            trace_uid=log.traceUid,
            timestamp=log.timestamp,
        )
        for logger in context.data_reporters:
            await logger.log(entry=entry)


@router.delete("/logs", summary="clear logs")
async def clear_logs(request: Request):
    """
    Clear all the logs in memory.

    Parameters:
        request: incoming request

    Return:
        None
    """

    context = Context.from_request(request=request)
    logger = cast(InMemoryReporter, context.logs_reporters[0])
    logger.clear()


def get_status(log: LogEntry, logger: InMemoryReporter):
    if log.context_id in logger.errors:
        return NodeLogStatus.FAILED

    if log.context_id in logger.futures:
        if log.context_id in logger.futures_succeeded:
            return NodeLogStatus.SUCCEEDED
        if log.context_id in logger.futures_failed:
            return NodeLogStatus.FAILED
        return NodeLogStatus.UNRESOLVED

    return NodeLogStatus.SUCCEEDED
