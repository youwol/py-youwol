# import asyncio
import shutil
import tempfile
from collections import Callable, Iterable
from enum import Enum
from pathlib import Path, PosixPath
from typing import Any, Union, Mapping, List
import re
from fastapi import HTTPException
import aiohttp

from starlette.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from youwol_utils import log_info

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]


def to_json(obj: BaseModel) -> JSON:

    def to_serializable(v):
        if isinstance(v, Path):
            return str(v)
        if isinstance(v, PosixPath):
            return str(v)
        if isinstance(v, Callable):
            return "function"
        if isinstance(v, Enum):
            return v.name
        if isinstance(v, Iterable) and not isinstance(v, list) and not isinstance(v, str):
            v = list(v)
        return v

    base = obj.dict()

    def to_json_rec(_obj: Any):

        if isinstance(_obj, dict):
            for k, v in _obj.items():
                if not isinstance(v, dict) and not isinstance(v, list):
                    _obj[k] = to_serializable(v)
                if isinstance(v, dict):
                    to_json_rec(v)
                if isinstance(v, list):
                    for i, e in enumerate(v):
                        if not isinstance(e, dict) and not isinstance(e, list):
                            _obj[k][i] = to_serializable(e)
                        else:
                            to_json_rec(e)

    to_json_rec(base)
    return base


def sed_inplace(filename, pattern, repl):

    # Perform the pure-Python equivalent of in-place `sed` substitution: e.g.,
    # `sed -i -e 's/'${pattern}'/'${repl}' ${filename}"`.

    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)

    # For portability, NamedTemporaryFile() defaults to mode "w+b" (i.e., binary
    # writing with updating). This is usually a good thing. In this case,
    # however, binary writing imposes non-trivial encoding constraints trivially
    # resolved by switching to text writing. Let's do that.
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        with open(filename) as src_file:
            for line in src_file:
                tmp_file.write(pattern_compiled.sub(repl, line))

    # Overwrite the original file with the munged temporary file in a
    # manner preserving file attributes (e.g., permissions).
    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)


async def start_web_socket(ws: WebSocket):
    while True:
        try:
            _ = await ws.receive_text()
        except WebSocketDisconnect:
            log_info(f'{ws.scope["client"]} - "WebSocket {ws.scope["path"]}" [disconnected]')
            break
