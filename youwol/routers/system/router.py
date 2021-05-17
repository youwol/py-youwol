import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, WebSocket

from utils_low_level import start_web_socket
from youwol.web_socket import WebSocketsCache

from starlette.requests import Request
from pydantic import BaseModel


router = APIRouter()


class FolderContentResp(BaseModel):
    configurations: List[str]
    files: List[str]
    folders: List[str]


class FolderContentBody(BaseModel):
    path: List[str]


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.system = ws
    await ws.send_json({})
    await start_web_socket(ws)


@router.post("/folder-content",
             response_model=FolderContentResp,
             summary="return the items in target folder")
async def folder_content(
        request: Request,
        body: FolderContentBody
        ):
    def is_conf_file(filename: str):
        if '.py' not in filename:
            return False
        content = (path / filename).read_text()
        if "async def configuration" in content and "UserConfiguration" in content:
            return True
        return False
    path = Path('/'.join(body.path))
    items = os.listdir(path)
    configurations = [item for item in items if os.path.isfile(path / item) and is_conf_file(item)]
    return FolderContentResp(
        configurations=configurations,
        files=[item for item in items if os.path.isfile(path / item) and item not in configurations],
        folders=[item for item in items if os.path.isdir(path / item)])
