import json
from pathlib import Path
from typing import List, Dict, NamedTuple, Any, Union, Callable, Awaitable, cast, Mapping

import aiohttp
from pydantic import BaseModel

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


async def get_remote_auth_token(username: str, pwd: str, client_id: str, client_secret: str):

    form = aiohttp.FormData()
    form.add_field("username", username)
    form.add_field("password", pwd)
    form.add_field("client_id", client_id)
    form.add_field("grant_type", "password")
    form.add_field("client_secret", client_secret)
    form.add_field("scope", "email profile youwol_dev")
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
    url: str


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


class General(BaseModel):
    systemFolder: TPath
    databasesFolder: TPath

    usersInfo: TPath
    userInfo: Union[None,
                    UserInfo,
                    Callable[[Context], Awaitable[UserInfo]]
                    ] = None

    secretsFile: TPath = None
    remoteGateways: List[RemoteGateway] = []
    localGateway: LocalGateway = LocalGateway()
    defaultPublishLocation: TPath = Path("private/default-publish")
    pinnedPaths: Dict[str, TPath] = {}

    async def get_user_info(self, context: Context) -> UserInfo:

        if isinstance(self.userInfo, UserInfo):
            return self.userInfo

        if isinstance(self.userInfo, Callable):
            getter = cast(Callable[[Context], Awaitable[any]], self.userInfo)
            return await getter(context)

        users_info = parse_json(self.usersInfo)
        if context.config.userEmail in users_info:
            return UserInfo(**users_info[context.config.userEmail])

        return UserInfo(
            id="anonymous",
            name="anonymous",
            email="",
            memberOf=["/youwol-users"]
            )

    def get_users_list(self) -> List[str]:
        secrets = parse_json(self.secretsFile)
        identified = secrets['identities'].keys() if 'identities' in secrets else []

        return list(identified) + ["anonymous"]

    async def get_auth_token(self, remote_env: str, context: Context):
        username = context.config.userId
        secrets = parse_json(self.secretsFile)
        client_id = secrets[remote_env]['clientId']
        client_secret = secrets[remote_env]['clientSecret']
        pwd = secrets[username]['clientSecret']
        return await get_remote_auth_token(
            username=username,
            pwd=pwd,
            client_id=client_id,
            client_secret=client_secret,
            )

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


class YouwolConfiguration(NamedTuple):

    http_port: int

    userEmail: Union[str, None]

    userConfig: UserConfiguration

    pathsBook: PathsBook

    localClients: LocalClients

    configurationParameters: ConfigParameters = ConfigParameters(parameters={})

    cache: Dict[str, Any] = {}
