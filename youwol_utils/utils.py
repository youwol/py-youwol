import asyncio
import itertools
import json
import os
from pathlib import Path
from typing import Union, List, cast, Mapping

import aiohttp
from fastapi import HTTPException
from starlette.requests import Request

from youwol_utils.clients.utils import raise_exception_from_response, to_group_id, to_group_scope
from youwol_utils.clients.types import DocDb

flatten = itertools.chain.from_iterable


def find_platform_path():
    return Path(__file__.split('/services')[0])


def user_info(request: Request):
    return request.state.user_info


def private_group_id(user):
    return f"private_{user['sub']}"


def is_authorized_write(request: Request, group_id):
    user = user_info(request)
    group_ids = get_user_group_ids(user)
    if group_id not in group_ids:
        return False

    permissions = {
        '/youwol-users': ['greinisch@youwol.com']
        }
    scope = to_group_scope(group_id)
    if scope in permissions:
        return user['preferred_username'] in permissions[scope]

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


def full_local_fake_user(request):
    user_name = request.headers.get('user-name', "fake_account@youwol.com")

    if user_name == "public":
        return {
            "sub": to_group_id(user_name), "email_verified": True, "name": "public account",
            "preferred_username": "public account", "email": "public-account@youwol.com",
            "memberof": [
                "/youwol-users"
                ],
            }
    if user_name == "test":
        return {
            "sub": to_group_id(user_name), "email_verified": True, "name": "test account",
            "preferred_username": "test account", "email": "test-account@youwol.com",
            "memberof": ["/youwol-users/postman-tester/subchildtest1",
                         "/youwol-users/postman-tester/subchildtest2",
                         "/youwol-users/youwol-devs",
                         ],
            }
    return {
        "sub": "82bcba26-65d7-4072-afc4-a28bb58611c4",
        "email_verified": True,
        "name": "test account",
        "preferred_username": user_name,
        "memberof": [
            "/youwol-users/postman-tester/subchildtest1",
            "/youwol-users/postman-tester/subchildtest2",
            "/youwol-users/youwol-devs",
            "/youwol-users/arche"
            ],
        "email": user_name,
        }


async def get_access_token(client_id: str, client_secret: str, client_scope: str, openid_host: str):

    body = {
        "client_id": client_id,
        "grant_type": "client_credentials",
        "client_secret": client_secret,
        "scope": client_scope
        }
    url = f"https://{openid_host}/auth/realms/youwol/protocol/openid-connect/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with await session.post(url, data=body, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            await raise_exception_from_response(resp)


async def get_headers_auth_admin_from_env():
    client_id = os.getenv("AUTH_CLIENT_ID")
    client_secret = os.getenv("AUTH_CLIENT_SECRET")
    client_scope = os.getenv("AUTH_CLIENT_SCOPE")
    openid_host = os.getenv("AUTH_HOST")
    resp = await get_access_token(client_id=client_id, client_secret=client_secret, client_scope=client_scope,
                                  openid_host=openid_host)
    access_token = resp['access_token']
    return {"Authorization": f"Bearer {access_token}"}


async def get_headers_auth_admin_from_secrets_file(file_path: Path, url_cluster: str, openid_host: str):

    secret = json.loads(file_path.read_text())[url_cluster]
    resp = await get_access_token(secret["clientId"], secret["clientSecret"], secret["scope"], openid_host=openid_host)
    access_token = resp['access_token']
    return {"Authorization": f"Bearer {access_token}"}


def generate_headers_downstream(incoming_headers):
    headers = {}
    if "Authorization" in incoming_headers:
        headers["Authorization"] = incoming_headers.get("Authorization")
    if "user-name" in incoming_headers:
        headers["user-name"] = incoming_headers.get("user-name")

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


def get_content_type(file_name: str):
    extensions = file_name.split('.')[1:]
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
    return "application/octet-stream"


def get_content_encoding(file_name: str):

    extension = file_name.split('.')[-1]
    if extension == "br":
        return "br"
    if extension == "gzip":
        return "gzip"

    return ""


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
