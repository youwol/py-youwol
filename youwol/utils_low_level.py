import asyncio
import importlib
import re
import shutil
import sys
import tempfile
from aiostream import stream
from collections import Callable, Iterable
from enum import Enum
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path, PosixPath
from typing import Any, Union, Mapping, List, Type, cast, TypeVar, Optional

import aiohttp
from aiohttp import ClientSession, TCPConnector
from fastapi import HTTPException
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket, WebSocketDisconnect

from youwol_utils import log_info
from youwol_utils.context import Context

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


T = TypeVar('T')


def get_object_from_module(
        module_absolute_path: Path,
        object_or_class_name: str,
        object_type: Type[T],
        additional_src_absolute_paths: Optional[Union[Path, List[Path]]] = None,
        **object_instantiation_kwargs
) -> T:

    if additional_src_absolute_paths is None:
        additional_src_absolute_paths = []

    if isinstance(additional_src_absolute_paths, Path):
        additional_src_absolute_paths = [additional_src_absolute_paths]

    for path in additional_src_absolute_paths:
        if path not in sys.path:
            sys.path.append(str(path))

    def get_instance_from_module(imported_module):
        if not hasattr(imported_module, object_or_class_name):
            raise Exception(f"{module_absolute_path} : Expected class '{object_or_class_name}' not found")

        maybe_class_or_var = imported_module.__getattribute__(object_or_class_name)

        if isinstance(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var)

        if issubclass(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var(**object_instantiation_kwargs))

        raise Exception(f"{module_absolute_path} : Expected class '{object_or_class_name}'"
                        f" does not implements expected type '{object_type}")

    module_name = module_absolute_path.stem
    try:
        loader = SourceFileLoader(module_name, str(module_absolute_path))
        spec = spec_from_loader(module_name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        instance = get_instance_from_module(module)
    except SyntaxError as e:
        raise Exception(f"{module_absolute_path} : Syntax error '{e}'")
    except NameError as e:
        raise Exception(f"{module_absolute_path} :Name error '{e}")

    return instance


def assert_python():
    print(f"Running with python:\n\t{sys.executable}\n\t{sys.version}")
    version_info = sys.version_info
    if not ((version_info.major == 3 and version_info.minor == 10) or
            (version_info.major == 3 and version_info.minor == 9) or
            (version_info.major == 3 and version_info.minor == 8) or
            (version_info.major == 3 and version_info.minor == 7)):
        print(f"""Your version of python is not compatible with py-youwol:
        Recommended: 3.9.x""")
        exit(1)


async def execute_shell_cmd(cmd: str, context: Context):
    p = await asyncio.create_subprocess_shell(
        cmd=cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True
    )
    outputs = []
    async with stream.merge(p.stdout, p.stderr).stream() as messages_stream:
        async for message in messages_stream:
            outputs.append(message.decode('utf-8'))
            await context.info(text=outputs[-1], labels=["BASH"])
    await p.communicate()

    return p.returncode, outputs
