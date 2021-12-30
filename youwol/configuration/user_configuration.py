import json
from pathlib import Path
from typing import List, Dict, NamedTuple, Union, Callable, Awaitable, Mapping, Any, Optional
from fastapi import HTTPException
import aiohttp
from pydantic import BaseModel


TPath = Union[str, Path]

Context = 'youwol.context.Context'
YouwolConfiguration = 'youwol.configuration.YouwolConfiguration'


def parse_json(path: Union[str, Path]):
    return json.loads(open(str(path)).read())


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

T = 'T'


class Case(NamedTuple):
    when: Union[bool, Callable[[], bool]]
    result: Union[Callable[[], T], Callable[[], Awaitable[T]]]


async def switch(default: T, cases: List[Case]) -> T:
    for case in cases:
        if case.when:
            raw_r = case.result
            if isinstance(raw_r, Awaitable):
                return await raw_r
            return raw_r
    return default


class RemoteGateway(BaseModel):
    name: str
    host: str
    metadata: Dict[str, str]


class LocalGateway(BaseModel):
    withHeaders: Union[None, Mapping[str, str], Callable[[Context], Awaitable[Mapping[str, str]]]] = None

    async def with_headers(self, context: Context) -> Mapping[str, str]:
        return await switch(
            default={},
            cases=[
                Case(when=isinstance(self.withHeaders, Mapping), result=lambda: self.withHeaders),
                Case(when=isinstance(self.withHeaders, Callable), result=lambda: self.withHeaders(context))
                ]
            )


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    memberOf: List[str]


class Secret(BaseModel):
    clientId: str
    clientSecret: str


Url = str
JSON = Any


class Events(BaseModel):
    onLoad: Callable[[YouwolConfiguration, Context], Optional[Any]] = None


class CDN(BaseModel):
    liveServers: Dict[str, Union[str, int]] = {}
