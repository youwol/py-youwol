import importlib
import re
import shutil
import socket
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path
from typing import Union, List, Type, cast, TypeVar, Optional

import aiohttp
from aiohttp import ClientSession, TCPConnector
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket, WebSocketDisconnect

from youwol.environment.forward_declaration import YouwolEnvironment
from youwol_utils import log_info, assert_response
from youwol_utils.context import Context


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
    await ws.accept()
    await ws.send_json({})
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


async def redirect_api_remote(request: Request, context: Context):
    async with context.start(action="redirect API in remote") as ctx:
        # One of the header item leads to a server error ... for now only provide authorization
        # headers = {k: v for k, v in request.headers.items()}
        # headers = {"Authorization": request.headers.get("authorization")}

        env = await context.get("env", YouwolEnvironment)
        redirect_base_path = env.redirectBasePath
        return await redirect_request(
            incoming_request=request,
            origin_base_path="/api",
            destination_base_path=redirect_base_path,
            headers=ctx.headers(),
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
        await assert_response(response)
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
            raise NameError(f"{module_absolute_path} : Expected class '{object_or_class_name}' not found")

        maybe_class_or_var = imported_module.__getattribute__(object_or_class_name)

        if isinstance(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var)

        if issubclass(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var(**object_instantiation_kwargs))

        raise TypeError(f"{module_absolute_path} : Expected class '{object_or_class_name}'"
                        f" does not implements expected type '{object_type}")

    module_name = module_absolute_path.stem
    try:
        loader = SourceFileLoader(module_name, str(module_absolute_path))
        spec = spec_from_loader(module_name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        instance = get_instance_from_module(module)
    except SyntaxError as e:
        raise SyntaxError(f"{module_absolute_path} : Syntax error '{e}'")
    except NameError as e:
        raise NameError(f"{module_absolute_path} :Name error '{e}")

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


def assert_py_youwol_starting_preconditions(http_port: int):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = ("127.0.0.1", http_port)
    if a_socket.connect_ex(location) == 0:
        raise ValueError(f"The port {http_port} is already bound to a process")


def shutdown_daemon_script(pid: int) -> str:
    return f"""#!/bin/sh
py_youwol_pid={pid}
## Sanity check
program_name=$(ps -p $py_youwol_pid -o command=)
echo "$program_name" | grep -q 'youwol/main.py'
if [ $? -ne 0 ]; then
    echo "Pid $py_youwol_pid does not look like py-youwol - program name is '$program_name'
Aborting"
    exit
fi
kill $py_youwol_pid
timeout 10 tail --pid=$py_youwol_pid -f /dev/null
if [ $? -eq 0 ]; then
    echo "Successfully send kill signal"
else
    echo "Failed to send kill signal"
fi
"""
