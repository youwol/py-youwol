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
    files: list[str]
    folders: list[str]


class FolderContentBody(BaseModel):
    path: str


@router.get("/file/{rest_of_path:path}", summary="return file content")
async def get_file(rest_of_path: str):
    return FileResponse(rest_of_path)


@router.post(
    "/folder-content",
    response_model=FolderContentResp,
    summary="return the items in target folder",
)
async def folder_content(body: FolderContentBody):
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
    BaseModel conversion of LogEntry from youwol.utils
    """

    level: str
    attributes: dict[str, str]
    labels: list[str]
    text: str
    data: Optional[JSON]
    contextId: str
    parentContextId: Optional[str]
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
    pass


class NodeLogStatus(Enum):
    Succeeded = "Succeeded"
    Failed = "Failed"
    Unresolved = "Unresolved"


class NodeLogResponse(Log):
    failed: bool
    future: bool
    status: NodeLogStatus


class LogsResponse(BaseModel):
    logs: list[Log]


class NodeLogsResponse(BaseModel):
    logs: list[NodeLogResponse]


class PostLogBody(Log):
    traceUid: str


class PostLogsBody(BaseModel):
    logs: list[PostLogBody]


@router.get("/logs/", summary="return the logs")
async def query_logs(
    request: Request,
    from_timestamp: int = Query(alias="from-timestamp", default=time.time()),
    max_count: int = Query(alias="max-count", default=1000),
) -> NodeLogsResponse:
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


@router.get("/logs/{parent_id}", summary="return the logs")
async def get_logs(request: Request, parent_id: str):
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
