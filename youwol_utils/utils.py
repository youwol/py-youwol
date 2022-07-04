import asyncio
import base64
import itertools
import json
from enum import Enum
from pathlib import Path, PosixPath
from typing import Union, List, cast, Mapping, Callable, Iterable, Any, NamedTuple

import aiohttp
from fastapi import HTTPException
from pydantic import BaseModel
from starlette.requests import Request

from youwol_utils import JSON, to_group_id
from youwol_utils.clients.types import DocDb

flatten = itertools.chain.from_iterable


class YouwolHeaders(NamedTuple):
    #  About tracing & headers: https://www.w3.org/TR/trace-context/
    py_youwol_local_only = 'py-youwol-local-only'
    correlation_id = 'x-correlation-id'
    trace_id = 'x-trace-id'

    @staticmethod
    def get_correlation_id(request: Request):
        return request.headers.get(YouwolHeaders.correlation_id, None)

    @staticmethod
    def get_trace_id(request: Request):
        return request.headers.get(YouwolHeaders.trace_id, None)

    @staticmethod
    def get_py_youwol_local_only(request: Request):
        return request.headers.get(YouwolHeaders.py_youwol_local_only, None)


def find_platform_path():
    return Path(__file__.split('/services')[0])


def user_info(request: Request):
    return request.state.user_info


def get_user_id(request: Request):
    return user_info(request)['sub']


def private_group_id(user):
    return f"private_{user['sub']}"


def is_authorized_write(request: Request, group_id):
    user = user_info(request)
    group_ids = get_user_group_ids(user)
    if group_id not in group_ids:
        return False

    return True


def get_all_individual_groups(groups: List[str]) -> List[Union[str, None]]:
    def get_combinations(elements: List[str]):
        result = []
        for i in range(1, len(elements)):
            result.append('/'.join(elements[0:i]))
        return result

    parts = [group.split('/') for group in groups if group]
    parts_flat = flatten([get_combinations(part) for part in parts])
    parts_flat = [e for e in parts_flat if e] + cast(any, [None])
    return list(set(groups + parts_flat))


def get_user_group_ids(user) -> List[Union[str, None]]:
    group_ids = [to_group_id(g) for g in get_all_individual_groups(user["memberof"]) if g is not None]
    return [private_group_id(user)] + group_ids


def get_leaf_group_ids(user) -> List[Union[str, None]]:
    group_ids = [to_group_id(g) for g in user["memberof"] if g is not None]
    return [private_group_id(user)] + group_ids


def ensure_group_permission(request: Request, group_id: str):
    user = user_info(request)
    allowed_groups = get_user_group_ids(user)
    if group_id not in allowed_groups:
        raise HTTPException(status_code=401, detail=f"User can not get/post resource")


async def get_youwol_environment(port: int = 2000):
    url = f"http://localhost:{port}/admin/environment/configuration"
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with await session.post(url=url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.read())
            resp = await resp.json()
            return resp


async def reload_youwol_environment(port: int):
    url = f"http://localhost:{port}/admin/environment/configuration"
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with await session.post(url=url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.read())


def generate_headers_downstream(incoming_headers):
    headers = {}
    if "Authorization" in incoming_headers:
        headers["Authorization"] = incoming_headers.get("Authorization")

    if "user-name" in incoming_headers:
        headers["user-name"] = incoming_headers.get("user-name")

    if YouwolHeaders.py_youwol_local_only in incoming_headers:
        headers[YouwolHeaders.py_youwol_local_only] = \
            incoming_headers.get(YouwolHeaders.py_youwol_local_only)

    return headers


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def get_group(primary_key: str, primary_value: Union[str, float, int, bool], groups: List[str], doc_db: DocDb,
                    headers: Mapping[str, str]):
    requests = [doc_db.query(query_body=f"{primary_key}={primary_value}#1", owner=group, headers=headers)
                for group in groups]
    responses = await asyncio.gather(*requests)
    group = next((g for i, g in enumerate(groups) if responses[i]["documents"]), None)
    return group


def check_permission_or_raise(target_group: Union[str, None], allowed_groups: List[Union[None, str]]):
    if not target_group:
        return
    compatible_groups = [g for g in allowed_groups if target_group in g]
    if len(compatible_groups) == 0:
        raise HTTPException(status_code=401,
                            detail=f"scope '{target_group}' not included in user groups")


def get_content_type(file_name: Union[str, Path]):
    extensions = Path(file_name).name.split('.')[1:]
    if "json" in extensions:
        return "application/json"
    if "yaml" in extensions:
        return "application/yaml"
    if "js" in extensions:
        return "application/javascript;charset=UTF-8"
    if "css" in extensions:
        return "text/css"
    if "woff2" in extensions:
        return "font/woff2"
    if 'svg' in extensions:
        return "image/svg+xml"
    if 'png' in extensions:
        return "image/png"
    if 'txt' in extensions:
        return 'text/plain'
    if 'html' in extensions:
        return 'text/html'
    if 'wasm' in extensions:
        return 'application/wasm'
    return "application/octet-stream"


def get_content_encoding(file_name: Union[str, Path]):
    extension = Path(file_name).name.split('.')[-1]
    if extension == "br":
        return "br"
    if extension == "gzip":
        return "gzip"

    return "identity"


async def retrieve_user_info(auth_token: str, openid_host: str):
    headers = {"authorization": f"Bearer {auth_token}"}
    url = f"https://{openid_host}/auth/realms/youwol/protocol/openid-connect/userinfo"

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with await session.post(url=url, headers=headers) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.read())
            resp = await resp.json()
            return resp


async def get_myself_auth_token(secret_path: Path, openid_host):
    secret = json.loads(open(str(secret_path)).read())
    form = aiohttp.FormData()
    form.add_field("username", secret["myself"]["username"])
    form.add_field("password", secret["myself"]["password"])
    form.add_field("client_id", secret["dev.platform.youwol.com"]["clientId"])
    form.add_field("grant_type", "password")
    form.add_field("client_secret", secret["dev.platform.youwol.com"]["clientSecret"])
    form.add_field("scope", "email profile youwol_dev")
    url = f"https://{openid_host}/auth/realms/youwol/protocol/openid-connect/token"
    async with aiohttp.ClientSession() as session:
        async with await session.post(url=url, data=form) as resp:
            resp = await resp.json()
            return resp['access_token']


def exception_message(error: Exception):
    if isinstance(error, HTTPException):
        return error.detail

    return str(error)


def decode_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()


def encode_id(raw_id) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


def to_json(obj: BaseModel) -> JSON:
    def to_serializable(v):
        if isinstance(v, Path):
            return str(v)
        if isinstance(v, PosixPath):
            return str(v)
        if isinstance(v, Callable):
            return {}
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
