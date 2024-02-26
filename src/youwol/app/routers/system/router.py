# standard library
import functools
import os
import time

from enum import Enum
from pathlib import Path

# typing
from typing import cast

# third parties
import griffe

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from griffe.dataclasses import Module
from pydantic import BaseModel
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment, yw_config
from youwol.app.routers.backends.implementation import INSTALL_MANIFEST_FILE
from youwol.app.routers.environment.router import get_status_impl
from youwol.app.routers.system.documentation import (
    YOUWOL_MODULE,
    check_documentation,
    format_module_doc,
    init_classes,
    init_symbols,
)
from youwol.app.routers.system.documentation_models import (
    DocAnalysisResponse,
    DocCache,
    DocChildModulesResponse,
    DocModuleResponse,
)

# Youwol utilities
from youwol.utils import JSON
from youwol.utils.context import Context, InMemoryReporter, Label, LogEntry, LogLevel

router = APIRouter()


class FolderContentResp(BaseModel):
    """
    Describes a folder content.
    """

    files: list[str]
    """
    List of the path files name.
    """

    folders: list[str]
    """
    List of folders name.
    """


class FolderContentBody(BaseModel):
    """
    Body used to query folder content
    using [folder_content](@yw-nav-func:youwol.app.routers.system.router.folder_content).
    """

    path: str


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


class QueryRootLogsBody(BaseModel):
    fromTimestamp: int
    maxCount: int


class Log(BaseModel):
    """
    Base class for logs generated from a [context](@yw-nav-class:Context) object.
    """

    level: str
    """
    Log level (info, debug, warning, error).
    """

    attributes: dict[str, str]
    """
    Attributes associated to the log.
    """

    labels: list[str]
    """
    Labels associated to the log.
    """
    text: str
    """
    Message.
    """

    data: JSON | None
    """
    Eventual data.
    """

    contextId: str
    """
    ID of the context that was used to generate the log (see [Context](@yw-nav-class:Context)).
    """

    parentContextId: str | None
    """
    ID of the parent context of the context that was used to generate the log
    (see [Context](@yw-nav-class:Context)).
    """

    timestamp: float

    @staticmethod
    def from_log_entry(log_entry: LogEntry):
        return Log(
            level=log_entry.level.name,
            attributes=log_entry.attributes,
            labels=log_entry.labels,
            text=log_entry.text,
            data=log_entry.data,
            contextId=log_entry.context_id,
            parentContextId=log_entry.parent_context_id,
            timestamp=log_entry.timestamp,
        )


class LeafLogResponse(Log):
    """
    A leaf log corresponds to a message - there is no log that will have as
    [parentContextId](@yw-nav-attr:youwol.app.routers.system.router.Log.parentContextId)
    the [contextId](@yw-nav-attr:youwol.app.routers.system.router.Log.contextId) of this log.

    It is created when using *e.g.* [Context.info](@yw-nav-meth:Context.info).
    """


class NodeLogStatus(Enum):
    SUCCEEDED = "Succeeded"
    """
    The log has a succeeded status: it signals that the parent function has ran as expected.
    """

    FAILED = "Failed"
    """
    The log has a failed status: it signals that the parent function failed, the log content explains the reason.
    """

    UNRESOLVED = "Unresolved"
    """
    The log has a unresolved status: it signals that the parent function is unresolved yet, the log content
    explains the reason.
    """


class NodeLogResponse(Log):
    """
    A 'node' log is associated to a function execution, it is likely associated to children: the logs generated
    within the function.

    It is created when using *e.g.* [Context.start](@yw-nav-meth:Context.start).

    The children logs have as
    [parentContextId](@yw-nav-attr:youwol.app.routers.system.router.Log.parentContextId)
    the [contextId](@yw-nav-attr:youwol.app.routers.system.router.Log.contextId) of this log.
    """

    failed: bool
    """
    Whether the function has a failed status after leaving it (deprecated, see `status` attribute).
    """

    future: bool
    """
    Whether the log function a future status after leaving it (deprecated, see `status` attribute).
    """

    status: NodeLogStatus
    """
    Status of the function after leaving it.
    """


class LogsResponse(BaseModel):
    """
    Describes a list of logs.
    """

    logs: list[Log]


class NodeLogsResponse(BaseModel):
    """
    Describes a list of 'node' logs (associated to the execution of a function).
    """

    logs: list[NodeLogResponse]
    """
    Logs list
    """


class PostLogBody(Log):
    """
    Body for a single log description.
    """

    traceUid: str
    """
    This attribute is the root parent's context ID of the log (equivalent to the usual trace ID).
    """


class PostLogsBody(BaseModel):
    """
    Body of the end point defined by the function
     [post_logs](@yw-nav-func:youwol.app.routers.system.router.post_logs).
    """

    logs: list[PostLogBody]
    """
    List of the logs.
    """


class PostDataBody(BaseModel):
    """
    Body of the end point defined by the function
     [post_data](@yw-nav-func:youwol.app.routers.system.router.post_data).
    """

    data: list[PostLogBody]
    """
    List of the data.
    """


class BackendLogsResponse(BaseModel):
    logs: list[Log]
    server_outputs: list[str]
    install_outputs: list[str] | None


class UninstallResponse(BaseModel):
    """
    Response model when calling [uninstall](@yw-nav-func:youwol.app.routers.system.router.uninstall)
    """

    name: str
    """
    Backend name.
    """

    version: str
    """
    Backend version.
    """

    backendTerminated: bool
    """
    Whether the backend has been terminated (if it was running when uninstalled).
    """
    wasInstalled: bool
    """
    Whether the backend was already installed.
    """


class TerminateResponse(BaseModel):
    """
    Response model when calling [terminate](@yw-nav-func:youwol.app.routers.system.router.terminate)
    """

    name: str
    """
    Backend name.
    """

    version: str
    """
    Backend version.
    """

    wasRunning: bool
    """
    Whether the backend was running.
    """


@router.delete(
    "/backends/{name}/{version}/terminate",
    summary="Terminate a backend",
    response_model=TerminateResponse,
)
async def terminate(
    request: Request,
    name: str,
    version: str,
    env: YouwolEnvironment = Depends(yw_config),
):
    """
    Terminate a backend.

    Parameters:
        request: incoming request.
        name: Name if the backend.
        version: Version of the backend.
        env: Injected current YouwolEnvironment.
    Return:
        Termination details.
    """
    async with Context.start_ep(
        request=request,
    ) as ctx:
        proxied = env.proxied_backends.get(name=name, query_version=version)
        if proxied:
            await env.proxied_backends.terminate(
                name=name, version=version, context=ctx
            )
            await get_status_impl(request=request, context=ctx)

        return TerminateResponse(
            name=name, version=version, wasRunning=proxied is not None
        )


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
    Uninstall a backend, eventually terminate it if running.

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
        proxied = env.proxied_backends.get(name=name, query_version=version)
        if proxied:
            await env.proxied_backends.terminate(
                name=name, version=version, context=ctx
            )
            await get_status_impl(request=request, context=ctx)

        manifest = (
            env.pathsBook.local_cdn_component(name=name, version=version)
            / INSTALL_MANIFEST_FILE
        )
        manifest_removed = False
        if manifest.exists():
            manifest_removed = True
            manifest.unlink()

        return UninstallResponse(
            name=name,
            version=version,
            backendTerminated=proxied is not None,
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
        proxy = env.proxied_backends.get(name=name, query_version=version)
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
    Forward log entries to the [Context.logs_reporters](@yw-nav-attr:Context.logs_reporters).

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
    Forward data entries to the [Context.data_reporters](@yw-nav-attr:Context.data_reporters).

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


@router.get(
    "/documentation-check",
    summary="Check the inlined youwol documentation.",
    response_model=DocAnalysisResponse,
)
async def documentation_check(request: Request):
    """
    Check the inlined youwol documentation.

    Parameters:
        request: Incoming request
    Return:
        Analysis report.
    """
    async with Context.start_ep(request=request):
        root = cast(Module, griffe.load(YOUWOL_MODULE, submodules=True))
        return DocAnalysisResponse(crossLinkErrors=check_documentation(root))


@router.get(
    "/documentation/{rest_of_path:path}",
    summary="Retrieves the documentation of a given module from this python package.",
    response_model=DocModuleResponse,
)
async def get_documentation(request: Request, rest_of_path: str) -> DocModuleResponse:
    """
    Retrieves the documentation of a given module from this youwol package.

    Only documented symbols are exposed in the documentation (modules, classes, functions, variables, attributes,
    *etc.*). The returned module documentation provides the list of its submodules, that can be latter queried for
    documentation if needed.

    Guidelines for documenting python code:

    *  Use <a href="https://mkdocstrings.github.io/griffe/docstrings/" target="_blank">Google style</a>
     documentation for functions.
    *  Class attributes documentation comes after their declaration, do not include it in class documentation.
    *  For cross-reference of symbols, use a mark-down link with url given by **$Kind:$Path** where:
        *  **$Kind** is either `@yw-nav-mod`, `@yw-nav-class`, `@yw-nav-attr`, `@yw-nav-meth`, `@yw-nav-func`,
        `@yw-nav-glob`, to respectively link symbol of kind module, class, class' attribute,  class' method,
         function, global variable.
        *  **$Path** is the full (including file) 'pythonic' path to the symbol, starting with `youwol`.

    Note:
        Some section id acts as identifier for rendering: `example`, `warning`

    Parameters:
        request: incoming request
        rest_of_path: path of the module separated with **'/'**; e.g. 'youwol/app/environment'. If empty, returns
            an 'empty' response with 'youwol' as unique child module
             (see <a href="@yw-nav-attr:youwol.app.routers.system.models.DocModuleResponse.childrenModules">
            DocModuleResponse.childrenModules</a>)

    Return:
        Module documentation
    """

    async with Context.start_ep(request=request):
        init_classes()
        DocCache.global_doc = DocCache.global_doc or cast(
            Module, griffe.load(YOUWOL_MODULE, submodules=True)
        )
        DocCache.all_symbols = init_symbols(DocCache.global_doc)
        if rest_of_path in DocCache.modules_doc:
            return DocCache.modules_doc[rest_of_path]
        root = rest_of_path == ""
        module_name = (
            rest_of_path.strip("/")
            .replace("/", ".")
            .replace(YOUWOL_MODULE, "")
            .strip(".")
        )
        try:
            module_doc = functools.reduce(
                lambda acc, e: acc.modules[e] if e else acc,
                module_name.split("."),
                DocCache.global_doc,
            )
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail=f"The module '{module_name}' is not part of youwol.",
            )
        griffe_doc = cast(Module, module_doc)
        if root:
            return DocModuleResponse(
                name="",
                path="",
                docstring=[],
                childrenModules=[
                    DocChildModulesResponse(
                        name=YOUWOL_MODULE,
                        path=YOUWOL_MODULE,
                        isLeaf=False,
                    )
                ],
                classes=[],
                functions=[],
                attributes=[],
                files=[],
            )

        doc_response = format_module_doc(griffe_doc=griffe_doc, path=module_name)
        DocCache.modules_doc[rest_of_path] = doc_response
        return doc_response
