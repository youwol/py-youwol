# standard library
import base64
import datetime
import itertools

from collections.abc import Iterable
from enum import Enum
from pathlib import Path, PosixPath

# typing
from typing import Any, Callable, Optional, Union, cast

# third parties
import aiohttp

from fastapi import HTTPException
from pydantic import BaseModel
from starlette.datastructures import Headers
from starlette.requests import Request

# Youwol utilities
from youwol.utils.clients.utils import to_group_id
from youwol.utils.types import JSON, AnyDict

flatten = itertools.chain.from_iterable


class YouwolHeaders:
    """
    Gather headers and operations on headers related to Youwol.
    """

    #  About tracing & headers: https://www.w3.org/TR/trace-context/
    py_youwol_local_only: str = "py-youwol-local-only"
    """
    If this header is true, no operation involving the remote ecosystem is enabled.
    """
    youwol_origin: str = "youwol-origin"
    correlation_id: str = "x-correlation-id"
    """
    Correlation id (see [trace & context](https://www.w3.org/TR/trace-context/)).
    """
    trace_id: str = "x-trace-id"
    """
    Trace id (see [trace & context](https://www.w3.org/TR/trace-context/)).
    """

    py_youwol_port: str = "py-youwol-port"
    """
    Convey the port on which py-youwol is serving on `local-host`.

    This is useful when *e.g.* writing an external backends connected using
    a [RedirectSwitch](@yw-nav-class:youwol.app.environment.models.models_config.RedirectSwitch) in which
    requests to the youwol local server are executed.
    """

    @staticmethod
    def get_correlation_id(request: Request) -> Optional[str]:
        """

        Parameters:
            request: incoming request
        Return:
            Correlation id of the request, if provided.
        """
        return request.headers.get(YouwolHeaders.correlation_id, None)

    @staticmethod
    def get_trace_id(request: Request) -> Optional[str]:
        """

        Parameters:
            request: incoming request
        Return:
            Trace id of the request, if provided.
        """
        return request.headers.get(YouwolHeaders.trace_id, None)

    @staticmethod
    def get_py_youwol_local_only(request: Request) -> Optional[str]:
        """

        Parameters:
            request: incoming request
        Return:
            The value of the header 'py-youwol-local-only' if included in the request.
        """
        return request.headers.get(YouwolHeaders.py_youwol_local_only, None)


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


def get_all_individual_groups(groups: list[str]) -> list[str]:
    def get_combinations(elements: list[str]):
        result = []
        for i in range(1, len(elements)):
            result.append("/".join(elements[0:i]))
        return result

    parts = [group.split("/") for group in groups if group]
    parts_flat_chained = flatten([get_combinations(part) for part in parts])
    parts_flat = [e for e in parts_flat_chained if e] + cast(Any, [None])
    return list(set(groups + parts_flat))


def get_user_group_ids(user) -> list[str]:
    group_ids = [
        to_group_id(g)
        for g in get_all_individual_groups(user["memberof"])
        if g is not None
    ]
    return [private_group_id(user)] + group_ids


def get_leaf_group_ids(user) -> list[str]:
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
    from_req_fwd: Callable[[list[str]], list[str]] = lambda _keys: [],
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
    target_group: Union[str, None], allowed_groups: list[str]
):
    if not target_group:
        return
    compatible_groups = [g for g in allowed_groups if target_group in g]
    if len(compatible_groups) == 0:
        raise HTTPException(
            status_code=401,
            detail=f"scope '{target_group}' not included in user groups",
        )


def get_content_type(file_name: Union[str, Path]) -> str:
    """
    Return a guessed content type from the extension.

    Parameters:
        file_name: Name or path of the file.

    Return:
        The content-type, default is "application/octet-stream".
    """
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
    """
    Return a guessed content encoding from the extension.

    Parameters:
        file_name: Name or path of the file.

    Return:
        The content-type, default is "identity".
    """
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
    if isinstance(v, datetime.datetime):
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


def to_json_rec(_obj: Union[AnyDict, list[Any], JSON]):
    def process_value(value):
        if is_json_leaf(value):
            return to_serializable_json_leaf(value)
        if isinstance(k, BaseModel):
            return to_json_rec(value.dict())
        return to_json_rec(value)

    if isinstance(_obj, dict):
        r_dict = {}
        for k, v in _obj.items():
            r_dict[k] = process_value(v)
        return r_dict

    if isinstance(_obj, list):
        r_list = []
        for k in _obj:
            r_list.append(process_value(k))
        return r_list

    return {}


def to_json(obj: Union[BaseModel, JSON]) -> JSON:
    base = obj.dict() if isinstance(obj, BaseModel) else obj
    return to_json_rec(base)
