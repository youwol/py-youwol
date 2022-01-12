import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, WebSocket

from youwol.utils_low_level import start_web_socket
from youwol.web_socket import WebSocketsStore

from pydantic import BaseModel
from fastapi.responses import FileResponse

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
