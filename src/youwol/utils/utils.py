# standard library
import base64
import itertools

from datetime import datetime
from enum import Enum
from pathlib import Path, PosixPath

# typing
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Set, Union, cast

# third parties
import aiohttp

from fastapi import HTTPException
from pydantic import BaseModel
from starlette.datastructures import Headers
from starlette.requests import Request

# Youwol utilities
from youwol.utils.clients.utils import to_group_id
from youwol.utils.types import JSON

flatten = itertools.chain.from_iterable


class YouwolHeaders(NamedTuple):
    #  About tracing & headers: https://www.w3.org/TR/trace-context/
    py_youwol_local_only = "py-youwol-local-only"
    youwol_origin = "youwol-origin"
    correlation_id = "x-correlation-id"
    trace_id = "x-trace-id"
    muted_http_errors = "muted_http_errors"

    @staticmethod
    def get_correlation_id(request: Request):
        return request.headers.get(YouwolHeaders.correlation_id, None)

    @staticmethod
    def get_trace_id(request: Request):
        return request.headers.get(YouwolHeaders.trace_id, None)

    @staticmethod
    def get_py_youwol_local_only(request: Request):
        return request.headers.get(YouwolHeaders.py_youwol_local_only, None)

    @staticmethod
    def get_muted_http_errors(request: Request) -> Set[int]:
        raw_header = request.headers.get(YouwolHeaders.muted_http_errors, None)
        return set() if not raw_header else {int(s) for s in raw_header.split(",")}

    @staticmethod
    def patch_request_mute_http_headers(request: Request, status_muted: Set[int]):
        header = (
            YouwolHeaders.muted_http_errors.encode(),
            ",".join(str(s) for s in status_muted).encode(),
        )
        request.headers.__dict__["_list"].append(header)


def user_info(request: Request):
    return request.state.user_info


def get_user_id(request: Request):
    return user_info(request)["sub"]


def private_group_id(user) -> str:
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
            result.append("/".join(elements[0:i]))
        return result

    parts = [group.split("/") for group in groups if group]
    parts_flat = flatten([get_combinations(part) for part in parts])
    parts_flat = [e for e in parts_flat if e] + cast(any, [None])
    return list(set(groups + parts_flat))


def get_user_group_ids(user) -> List[Union[str, None]]:
    group_ids = [
        to_group_id(g)
        for g in get_all_individual_groups(user["memberof"])
        if g is not None
    ]
    return [private_group_id(user)] + group_ids


def get_leaf_group_ids(user) -> List[Union[str, None]]:
    group_ids = [to_group_id(g) for g in user["memberof"] if g is not None]
    return [private_group_id(user)] + group_ids


def ensure_group_permission(request: Request, group_id: str):
    user = user_info(request)
    allowed_groups = get_user_group_ids(user)
    if group_id not in allowed_groups:
        raise HTTPException(status_code=401, detail="User can not get/post resource")


async def get_youwol_environment(port: int = 2000):
    url = f"http://localhost:{port}/admin/environment/configuration"
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(verify_ssl=False)
    ) as session:
        async with await session.post(url=url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.read())
            resp = await resp.json()
            return resp


async def reload_youwol_environment(port: int):
    url = f"http://localhost:{port}/admin/environment/configuration"
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(verify_ssl=False)
    ) as session:
        async with await session.post(url=url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.read())


def generate_headers_downstream(
    incoming_headers: Headers,
    from_req_fwd: Callable[[List[str]], List[str]] = lambda _keys: [],
):
    # the following headers are set when a request is sent anyway
    black_list = ["content-type", "content-length", "content-encoding"]
    headers_keys = [h.lower() for h in incoming_headers.keys()]
    to_propagate = [h.lower() for h in from_req_fwd(headers_keys)] + [
        "authorization",
        YouwolHeaders.py_youwol_local_only,
    ]

    return {
        k: v
        for k, v in incoming_headers.items()
        if k.lower() in to_propagate and k.lower() not in black_list
    }


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def check_permission_or_raise(
    target_group: Union[str, None], allowed_groups: List[Union[None, str]]
):
    if not target_group:
        return
    compatible_groups = [g for g in allowed_groups if target_group in g]
    if len(compatible_groups) == 0:
        raise HTTPException(
            status_code=401,
            detail=f"scope '{target_group}' not included in user groups",
        )


def get_content_type(file_name: Union[str, Path]):
    extensions = Path(file_name).name.split(".")[1:]
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
    if "svg" in extensions:
        return "image/svg+xml"
    if "png" in extensions:
        return "image/png"
    if "pdf" in extensions:
        return "application/pdf"
    if "txt" in extensions:
        return "text/plain"
    if "html" in extensions:
        return "text/html"
    if "wasm" in extensions:
        return "application/wasm"
    return "application/octet-stream"


def get_content_encoding(file_name: Union[str, Path]):
    extension = Path(file_name).name.split(".")[-1]
    if extension == "br":
        return "br"
    if extension == "gzip":
        return "gzip"

    return "identity"


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


def to_serializable_json_leaf(v):
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, PosixPath):
        return str(v)
    if isinstance(v, Callable):
        return {}
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, Iterable) and not isinstance(v, list) and not isinstance(v, str):
        v = list(v)
    if isinstance(v, datetime):
        return str(v)
    if isinstance(v, (int, float, str, bool)):
        return v
    if v is None:
        return None
    # This is the case of a custom class not deriving from 'BaseModel' => no serialization
    return {}


def is_json_leaf(v):
    return (
        not isinstance(v, dict)
        and not isinstance(v, list)
        and not isinstance(v, BaseModel)
    )


def to_json_rec(_obj: Union[Dict[str, Any], List[Any]]):
    result = {}

    def process_value(value):
        if is_json_leaf(value):
            return to_serializable_json_leaf(value)
        if isinstance(k, BaseModel):
            return to_json_rec(value.dict())
        return to_json_rec(value)

    if isinstance(_obj, dict):
        result = {}
        for k, v in _obj.items():
            result[k] = process_value(v)

    if isinstance(_obj, list):
        result = []
        for k in _obj:
            result.append(process_value(k))

    return result


def to_json(obj: Union[BaseModel, Dict[str, Any]]) -> JSON:
    base = obj.dict() if isinstance(obj, BaseModel) else obj
    return to_json_rec(base)
