from typing import Mapping, Union, NamedTuple, List

from aiohttp import ClientResponse
import base64

from fastapi import HTTPException


class GroupInfo(NamedTuple):
    id: str
    owner: Union[str, None]
    scope: str


def to_group_id(group_path: Union[str, None]) -> str:
    if group_path == 'private':
        return 'private'
    b = str.encode(group_path)
    return base64.urlsafe_b64encode(b).decode()


def group_info(group_id: str):
    return GroupInfo(id=group_id, owner=to_group_owner(group_id), scope=to_group_scope(group_id))


def to_group_scope(group_id: str) -> str:
    if "private" in group_id:
        return 'private'
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()


def to_group_owner(group_id: str) -> Union[str, None]:
    if 'private' in group_id:
        return None
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()


def is_child_group(child_group_id, parent_group_id):

    if child_group_id == parent_group_id:
        return True

    child_scope = to_group_scope(child_group_id)
    parent_scope = to_group_scope(parent_group_id)
    if child_scope == 'private' or parent_scope == 'private':
        return child_group_id == parent_group_id

    if len(parent_scope) > len(child_scope):
        return False

    return child_scope[0:len(parent_scope)] == parent_scope


def ancestors_group_id(group_id):

    scope = to_group_scope(group_id)
    if scope == "private":
        return []

    items = [scope for scope in scope.split('/') if scope != ""]
    paths = ['/'.join([""]+items[0:i+1]) for i, _ in enumerate(items)]
    ids = [to_group_id(p) for p in paths[0:-1]]
    ids.reverse()
    return ids


class YouWolException(HTTPException):
    def __init__(self, status_code: int, detail: str, **kwargs):
        self.exceptionType = "YouWolException"
        self.status_code = status_code
        self.detail = detail
        self.parameters = kwargs


class PackagesNotFound(YouWolException):
    def __init__(self, detail: str, packages: List[str], **kwargs):
        YouWolException.__init__(self, 404, detail, packages=packages, **kwargs)
        self.exceptionType = "PackagesNotFound"


def aiohttp_resp_parameters(resp: ClientResponse):

    return {
        "real_url": str(resp.request_info.real_url),
        "method": resp.request_info.method
        }


async def raise_exception_from_response(raw_resp: ClientResponse, **kwargs):

    detail = None

    print(f"HTTPException with status code {raw_resp.status}")
    parameters = {}
    try:
        resp = await raw_resp.json()
        if resp:
            detail = resp.get("detail", None) or resp.get("message", None) or ""
            parameters = resp.get("parameters", None) or {}
    except ValueError:
        detail = raw_resp.reason
    except Exception:
        pass

    detail = detail if detail else await raw_resp.text()

    if detail:
        print(f"detail:", detail)

    print(raw_resp)
    raise YouWolException(status_code=raw_resp.status, detail=detail, **{**kwargs, ** parameters} )


def get_default_owner(headers: Mapping[str, str]):
    return f"/{headers['user-name']}" if "user-name" in headers else "/default-username"


def get_valid_bucket_name(name):
    return name.replace('_', "-")


def get_valid_keyspace_name(name):
    return name.replace('-', "_")


def log_info(message, **kwargs):
    content = f"INFO:     {message}"
    for name, value in kwargs.items():
        content += "/n"
        content += f"{name} : {str(value)}"

    print(content)


def log_error(message, json=None):
    json_message = str(json) if json else ""
    print(f"ERROR:     {message}", json_message)
