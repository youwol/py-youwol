import os
import time
from pathlib import Path
from typing import List, cast, Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.requests import Request

from youwol.web_socket import AdminContextLogger, Log
from youwol_utils.context import Context

router = APIRouter()


class FolderContentResp(BaseModel):
    files: List[str]
    folders: List[str]


class FolderContentBody(BaseModel):
    path: str


@router.get("/file/{rest_of_path:path}",
            summary="return file content")
async def get_file(rest_of_path: str):

    return FileResponse(rest_of_path)


@router.post("/folder-content",
             response_model=FolderContentResp,
             summary="return the items in target folder")
async def folder_content(
        body: FolderContentBody
        ):

    path = Path(body.path)
    if not path.is_dir():
        return FolderContentResp(
            files=[],
            folders=[]
        )
    items = os.listdir(path)
    return FolderContentResp(
        files=[item for item in items if os.path.isfile(path / item)],
        folders=[item for item in items if os.path.isdir(path / item)]
    )


class QueryRootLogsBody(BaseModel):
    fromTimestamp: int
    maxCount: int


class LeafLogResponse(Log):
    pass


class NodeLogResponse(Log):
    failed: bool


class LogsResponse(BaseModel):
    logs: List[Log]


@router.get("/logs/", summary="return the logs")
async def query_logs(
        request: Request,
        from_timestamp: int = Query(alias='from-timestamp', default=time.time()),
        max_count: int = Query(alias='max-count', default=1000),
) -> LogsResponse:
    response: Optional[LogsResponse] = None
    async with Context.start_ep(
            action="query logs",
            with_attributes={"fromTimestamp": from_timestamp, "maxCount": max_count},
            response=lambda: response,
            request=request
    ) as ctx:
        logger = cast(AdminContextLogger, ctx.logger)
        logs = []
        for log in reversed(logger.root_node_logs):
            if log.timestamp > from_timestamp * 1000:
                pass
            failed = log.contextId in logger.errors
            logs.append(NodeLogResponse(**log.dict(), failed=failed))
            if len(logs) > max_count:
                break
        response = LogsResponse(logs=logs)
        return response


@router.get("/logs/{parent_id}",
            summary="return the logs")
async def get_logs(request: Request, parent_id: str):
    async with Context.start_ep(
            action="get logs",
            request=request
    ) as ctx:
        logger = cast(AdminContextLogger, ctx.logger)
        nodes_logs, leaf_logs, errors = logger.node_logs, logger.leaf_logs, ctx.logger.errors

        nodes: List[Log] = [NodeLogResponse(**log.dict(), failed=log.contextId in errors)
                            for log in nodes_logs
                            if log.parentContextId == parent_id]
        leafs: List[Log] = [LeafLogResponse(**log.dict())
                            for log in leaf_logs
                            if log.contextId == parent_id]

        return LogsResponse(logs=sorted(nodes + leafs, key=lambda n: n.timestamp))
