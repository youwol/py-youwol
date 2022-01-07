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
from aiohttp import ClientSession, TCPConnector
from starlette.requests import Request
from starlette.responses import Response

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


async def get_public_user_auth_token(username: str, pwd: str, client_id: str, openid_host: str):

    form = aiohttp.FormData()
    form.add_field("username", username)
    form.add_field("password", pwd)
    form.add_field("client_id", client_id)
    form.add_field("grant_type", "password")
    url = f"https://{openid_host}/auth/realms/youwol/protocol/openid-connect/token"
    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False),
            timeout=aiohttp.ClientTimeout(total=5)) as session:
        async with await session.post(url=url, data=form) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.read())
            resp = await resp.json()
            return resp['access_token']


async def redirect_api_remote(request: Request):
    # One of the header item leads to a server error ... for now only provide authorization
    # headers = {k: v for k, v in request.headers.items()}
    headers = {"Authorization": request.headers.get("authorization")}

    return await redirect_request(
        incoming_request=request,
        origin_base_path="/api",
        destination_base_path="https://gc.platform.youwol.com/api",
        headers=headers,
        )


async def redirect_request(
        incoming_request: Request,
        origin_base_path: str,
        destination_base_path: str,
        headers=None
        ):
    rest_of_path = incoming_request.url.path.split(origin_base_path)[1].strip('/')
    headers = {k: v for k, v in incoming_request.headers.items()} if not headers else headers
    redirect_url = f"{destination_base_path}/{rest_of_path}"

    async def forward_response(response):
        headers_resp = {k: v for k, v in response.headers.items()}
        content = await response.read()
        return Response(status_code=response.status, content=content, headers=headers_resp)

    params = incoming_request.query_params
    # after this eventual call, a subsequent call to 'body()' will hang forever
    data = await incoming_request.body() if incoming_request.method in ['POST', 'PUT', 'DELETE'] else None

    async with ClientSession(connector=TCPConnector(verify_ssl=False), auto_decompress=False) as session:

        if incoming_request.method == 'GET':
            async with await session.get(url=redirect_url, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'POST':
            async with await session.post(url=redirect_url, data=data, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'PUT':
            async with await session.put(url=redirect_url, data=data, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'DELETE':
            async with await session.delete(url=redirect_url, data=data,  params=params, headers=headers) as resp:
                return await forward_response(resp)
