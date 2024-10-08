# standard library
import base64
import datetime
import itertools
import json
import os
import zlib

from collections.abc import Callable, Iterable
from enum import Enum
from pathlib import Path, PosixPath

# typing
from typing import Any, cast

# third parties
import aiohttp

from fastapi import HTTPException
from pydantic import BaseModel
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response

# Youwol
import youwol

# Youwol utilities
from youwol.utils.clients.utils import to_group_id
from youwol.utils.context.models import TContextAttr
from youwol.utils.types import JSON, AnyDict

flatten = itertools.chain.from_iterable

PYPROJECT_TOML = "pyproject.toml"
"""
Filename of the `PYPROJECT_TOML`.
"""


class YwBrowserCacheDirective(BaseModel):
    """
    Cache directive to the intention of
    :class:`BrowserCacheStore <youwol.app.environment.browser_cache_store.BrowserCacheStore>`.
    """

    filepath: str
    """
    Path of the file on disk.
    """
    service: str
    """
    Name of the service that generated this directive.
    """


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

    trace_labels: str = "x-trace-labels"
    """
    Labels to associate with the trace, provided as a JSON array.
    """

    trace_attributes: str = "x-trace-attributes"
    """
    Attributes to associate with the trace, provided as a JSON dict.
    """

    py_youwol_port: str = "py-youwol-port"
    """
    Convey the port on which py-youwol is serving on `local-host`.

    This is useful when *e.g.* writing an external backends connected using
    a :class:`RedirectSwitch <youwol.app.environment.models.flow_switches.RedirectSwitch>` in which
    requests to the youwol local server are executed.
    """

    yw_browser_cache_directive = "yw_browser_cache_directive"
    """
    This header key is to be included to enable the
    :class:`BrowserCacheStore <youwol.app.environment.browser_cache_store.BrowserCacheStore>` to cache a response,
    see the function
    :attr:`set_yw_browser_cache_directive <youwol.utils.utils.YouwolHeaders.set_yw_browser_cache_directive>`.
    """

    backends_partition: str = "x-backends-partition"
    """
    Target partition regarding backends calls.
    """

    @staticmethod
    def get_correlation_id(request: Request) -> str | None:
        """
        Parameters:
            request: incoming request

        Returns:
            Correlation id of the request, if provided.
        """
        return request.headers.get(YouwolHeaders.correlation_id, None)

    @staticmethod
    def get_trace_id(request: Request) -> str | None:
        """
        Parameters:
            request: incoming request

        Returns:
            Trace id of the request, if provided.
        """
        return request.headers.get(YouwolHeaders.trace_id, None)

    @staticmethod
    def get_trace_labels(request: Request) -> list[str]:
        """

        Parameters:
            request: Incoming request.

        Returns:
            Trace's labels from the request's headers, if provided.

        Raise:
            `ValueError` when decoding the labels header failed.
        """
        raw = request.headers.get(YouwolHeaders.trace_labels, "[]")
        labels = json.loads(raw)
        if not isinstance(labels, list):
            raise ValueError("Trace label's header should be provided as an array.")
        return [str(label) for label in labels]

    @staticmethod
    def get_trace_attributes(request: Request) -> dict[str, TContextAttr]:
        """

        Parameters:
            request: Incoming request.

        Returns:
            Trace's attributes from the request's headers, if provided.

        Raise:
            `ValueError` when decoding the attributes header failed.
        """
        raw = request.headers.get(YouwolHeaders.trace_attributes, "{}")

        attributes = json.loads(raw)
        if not isinstance(attributes, dict):
            raise ValueError(
                "Trace attribute's header should be provided as a dictionary."
            )
        return attributes

    @staticmethod
    def get_py_youwol_local_only(request: Request) -> str | None:
        """

        Parameters:
            request: incoming request

        Returns:
            The value of the header 'py-youwol-local-only' if included in the request.
        """
        return request.headers.get(YouwolHeaders.py_youwol_local_only, None)

    @staticmethod
    def get_youwol_browser_cache_info(
        response: Response,
    ) -> YwBrowserCacheDirective | None:
        """
        Retrieves an eventual directive regarding caching within
        :class:`BrowserCacheStore <youwol.app.environment.browser_cache_store.BrowserCacheStore>`.

        Parameters:
            response: Response to retrieve the directive from, using the header
                :attr:`yw_browser_cache_directive <youwol.utils.utils.YouwolHeaders.yw_browser_cache_directive>`.

        Returns:
            The directive if found.
        """
        info = response.headers.get(YouwolHeaders.yw_browser_cache_directive, None)
        if info:
            return YwBrowserCacheDirective(**json.loads(info))

        return None

    @staticmethod
    def set_yw_browser_cache_directive(
        response: Response, directive: YwBrowserCacheDirective
    ) -> None:
        """
        Set directive for YouWol's
        :class:`BrowserCacheStore <youwol.app.environment.browser_cache_store.BrowserCacheStore>` to cache a response.

        Parameters:
            response: The response to instrument for caching.
            directive: Required information about the resource to be cached.
        """
        response.headers.append(
            YouwolHeaders.yw_browser_cache_directive, json.dumps(directive.dict())
        )

    @staticmethod
    def get_backends_partition(request: Request, default_id: str | None) -> str | None:
        """

        Parameters:
            request: incoming request

        Returns:
            Target partition ID, if available.
        """
        return request.headers.get(YouwolHeaders.backends_partition, default_id)


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
        YouwolHeaders.backends_partition,
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


def check_permission_or_raise(target_group: str | None, allowed_groups: list[str]):
    if not target_group:
        return
    compatible_groups = [g for g in allowed_groups if target_group in g]
    if not compatible_groups:
        raise HTTPException(
            status_code=401,
            detail=f"scope '{target_group}' not included in user groups",
        )


def get_content_type(file_name: str | Path) -> str:
    """
    Return a guessed content type from the extension.

    Parameters:
        file_name: Name or path of the file.

    Returns:
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


def get_content_encoding(file_name: str | Path) -> str:
    """
    Return a guessed content encoding from the extension.

    Parameters:
        file_name: Name or path of the file.

    Returns:
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


def json2uid(from_json: JSON) -> str:
    json_config = json.dumps(from_json, sort_keys=True)
    compressed_bytes = zlib.compress(json_config.encode("utf-8"))
    base64_bytes = base64.urlsafe_b64encode(compressed_bytes)
    return base64_bytes.decode("utf-8")


def uid2json(from_uid: str) -> JSON:
    compressed_bytes = base64.urlsafe_b64decode(from_uid)
    json_string = zlib.decompress(compressed_bytes).decode("utf-8")
    return json.loads(json_string)


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


def to_json_rec(_obj: AnyDict | list[Any] | JSON):
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


def to_json(obj: BaseModel | JSON) -> JSON:
    base = obj.dict() if isinstance(obj, BaseModel) else obj
    return to_json_rec(base)


def deep_merge(from_dict: AnyDict, with_dict: AnyDict):
    def deep_merge_impl(dict1: AnyDict | Any, dict2: AnyDict | Any):
        if not all(isinstance(d, dict) for d in [dict1, dict2]):
            return dict2

        merged = dict1.copy()
        for key, value in dict2.items():
            merged[key] = deep_merge_impl(merged.get(key, None), value)

        return merged

    return deep_merge_impl(from_dict, with_dict)


def yw_repo_path() -> Path:
    """Return the path of the py-youwol source repository, expected to contain `pyproject.toml`.

    Use environment variable `PY_YOUWOL_SOURCES`, if set.
    If not, assume running from sources, then fallback to search `pyproject.toml` in parents of
    current working directory.

    Raise:
        `RuntimeError`: If `pyproject.toml` cannot be found in `PY_YOUWOL_SOURCES`, if set,
        or in searched directories if not set.
    """

    py_youwol_sources = os.environ.get("PY_YOUWOL_SOURCES")
    if py_youwol_sources:
        pyproject_toml_path = (Path(py_youwol_sources) / PYPROJECT_TOML).absolute()
        if pyproject_toml_path.exists():
            return Path(py_youwol_sources).absolute()
        raise RuntimeError(
            f"Env `PY_YOUWOL_SOURCES` set to '{py_youwol_sources}' but '{str(pyproject_toml_path)}' not found"
        )

    path_youwol__init__ = Path(youwol.__file__).resolve()
    path_repo = path_youwol__init__.parent.parent.parent
    if (path_repo / PYPROJECT_TOML).exists():
        return path_repo.absolute()

    result = None
    candidate_dir = Path.cwd().resolve()
    while candidate_dir != candidate_dir.parent:
        if (candidate_dir / PYPROJECT_TOML).exists():
            result = candidate_dir
            break
        candidate_dir = candidate_dir.parent

    if result is None:
        raise RuntimeError(f"{PYPROJECT_TOML} not found")

    return result.absolute()


def yw_doc_version() -> str:
    """
    Retrieves the version of the YouWol documentation app.

    This function determines the version of the YouWol documentation app based on the version of the YouWol platform.
    Due to limitations in the semantic versioning supported for components in the CDN-backend service,
    a transformation is required from the YouWol version to the documentation app version.
    See :func:`publish_library <youwol.backends.cdn.root_paths.publish_library>`.

    Returns:
        Documentation app. version.
    """
    version = youwol.__version__

    # Order does matter in the following list, e.g. `0.1.8rc1.dev` -> `0.1.8-wip`
    wip_suffixes = ["rc", ".dev"]
    for suffix in wip_suffixes:
        if suffix in version:
            return f"{version.split(suffix, maxsplit=1)[0]}-wip"

    final_suffixes = [".post"]
    for suffix in final_suffixes:
        if suffix in version:
            return f"{version.split(suffix, maxsplit=1)[0]}"

    return version
