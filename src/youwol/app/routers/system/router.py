# standard library
import os
import time

from enum import Enum
from pathlib import Path

# typing
from typing import Optional, cast

# third parties
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.requests import Request

# Youwol utilities
from youwol.utils import JSON
from youwol.utils.context import Context, InMemoryReporter, LogEntry, LogLevel

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
    Base class for logs generated from a [context](@yw-nav-class:youwol.utils.context.Context) object.
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

    data: Optional[JSON]
    """
    Eventual data.
    """

    contextId: str
    """
    ID of the context that was used to generate the log (see [Context](@yw-nav-class:youwol.utils.context.Context)).
    """

    parentContextId: Optional[str]
    """
    ID of the parent context of the context that was used to generate the log
    (see [Context](@yw-nav-class:youwol.utils.context.Context)).
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

    It is created when using *e.g.* [Context.info](@yw-nav-meth:youwol.utils.context.Context.info).
    """


class NodeLogStatus(Enum):
    Succeeded = "Succeeded"
    """
    The log has a succeeded status: it signals that the parent function has ran as expected.
    """

    Failed = "Failed"
    """
    The log has a failed status: it signals that the parent function failed, the log content explains the reason.
    """

    Unresolved = "Unresolved"
    """
    The log has a unresolved status: it signals that the parent function is unresolved yet, the log content
    explains the reason.
    """


class NodeLogResponse(Log):
    """
    A 'node' log is associated to a function execution, it is likely associated to children: the logs generated
    within the function.

    It is created when using *e.g.* [Context.start](@yw-nav-meth:youwol.utils.context.Context.start).

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

    response: Optional[NodeLogsResponse] = None
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
    Add logs in memory.

    Parameters:
        request: incoming request
        body: description of the logs to add

    """
    context = Context.from_request(request=request)
    logger = cast(InMemoryReporter, context.logs_reporters[0])
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
        return NodeLogStatus.Failed

    if log.context_id in logger.futures:
        if log.context_id in logger.futures_succeeded:
            return NodeLogStatus.Succeeded
        if log.context_id in logger.futures_failed:
            return NodeLogStatus.Failed
        return NodeLogStatus.Unresolved

    return NodeLogStatus.Succeeded
