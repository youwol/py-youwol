# standard library
import base64
import functools
import json

from collections.abc import Mapping

# typing
from typing import NamedTuple

# third parties
from aiohttp import ClientResponse


class GroupInfo(NamedTuple):
    id: str
    owner: str | None
    scope: str


def to_group_id(group_path: str) -> str:
    if group_path == "private":
        return "private"
    b = str.encode(group_path)
    return base64.urlsafe_b64encode(b).decode()


def group_info(group_id: str):
    return GroupInfo(
        id=group_id, owner=to_group_owner(group_id), scope=to_group_scope(group_id)
    )


def to_group_scope(group_id: str) -> str:
    if "private" in group_id:
        return "private"
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()


def to_group_owner(group_id: str) -> str | None:
    if "private" in group_id:
        return None
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()


def is_child_group(child_group_id, parent_group_id):
    if child_group_id == parent_group_id:
        return True

    child_scope = to_group_scope(child_group_id)
    parent_scope = to_group_scope(parent_group_id)
    if child_scope == "private" or parent_scope == "private":
        return child_group_id == parent_group_id

    if len(parent_scope) > len(child_scope):
        return False

    return child_scope[0 : len(parent_scope)] == parent_scope


def ancestors_group_id(group_id):
    scope = to_group_scope(group_id)
    if scope == "private":
        return []

    items = [scope for scope in scope.split("/") if scope != ""]
    paths = ["/".join([""] + items[0 : i + 1]) for i, _ in enumerate(items)]
    ids = [to_group_id(p) for p in paths[0:-1]]
    ids.reverse()
    return ids


def aiohttp_resp_parameters(resp: ClientResponse):
    return {
        "real_url": str(resp.request_info.real_url),
        "method": resp.request_info.method,
    }


def get_default_owner(headers: Mapping[str, str]):
    return f"/{headers['user-name']}" if "user-name" in headers else "/default-username"


def get_valid_bucket_name(name: str) -> str:
    return name.replace("_", "-")


def log_info(message, **kwargs):
    content = f"INFO:     {message}"
    for name, value in kwargs.items():
        content += "/n"
        content += f"{name} : {str(value)}"

    print(content)


def log_error(message, json_data=None):
    content = f"ERROR:     {message}"
    if json_data:
        content += json.dumps(json_data, indent=4)
    print(content)


def auto_port_number(service_name: str):
    port = functools.reduce(lambda acc, e: acc + ord(e), service_name, 0)
    # need to check if somebody is already listening
    return 2000 + port % 1000
