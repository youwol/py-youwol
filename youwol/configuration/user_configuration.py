from datetime import datetime
import json
from pathlib import Path
from typing import List, Dict, NamedTuple, Any, Union, Callable, Awaitable, Mapping

import aiohttp
from pydantic import BaseModel

from models import ActionStep
from youwol.configuration.models_back import BackEnds
from youwol.configuration.models_base import ConfigParameters
from youwol.configuration.models_front import FrontEnds
from youwol.configuration.models_package import Packages
from youwol.configuration.paths import PathsBook
from youwol_utils import CdnClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.treedb.treedb import TreeDbClient

TPath = Union[str, Path]

Context = 'youwol.context.Context'


def parse_json(path: Union[str, Path]):
    return json.loads(open(str(path)).read())


async def get_public_user_auth_token(username: str, pwd: str, client_id: str):

    form = aiohttp.FormData()
    form.add_field("username", username)
    form.add_field("password", pwd)
    form.add_field("client_id", client_id)
    form.add_field("grant_type", "password")
    url = "https://auth.youwol.com/auth/realms/youwol/protocol/openid-connect/token"
    async with aiohttp.ClientSession() as session:
        async with await session.post(url=url, data=form) as resp:
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


class General(BaseModel):
    systemFolder: TPath
    databasesFolder: TPath

    usersInfo: TPath

    secretsFile: TPath = None
    remotesInfo: TPath = None
    localGateway: LocalGateway = LocalGateway()
    defaultPublishLocation: TPath = Path("private/default-publish")
    resources: Dict[str, Url] = {}

    def get_users_list(self) -> List[str]:
        users = list(parse_json(self.usersInfo)['users'].keys())
        return users

    def get_secret(self, remote_env: str):
        secrets = parse_json(self.secretsFile)
        return Secret(**secrets[remote_env])


class UserConfiguration(BaseModel):
    general: General
    packages: Packages = Packages()
    frontends: FrontEnds = FrontEnds()
    backends: BackEnds = BackEnds()

    class Config:
        json_encoders = {
            Path: lambda v: str(v)
            }


class LocalClients(NamedTuple):

    treedb_client: TreeDbClient
    assets_client: AssetsClient
    flux_client: FluxClient
    cdn_client: CdnClient
    assets_gateway_client: AssetsGatewayClient

