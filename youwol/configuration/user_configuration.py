from datetime import datetime
import json
from pathlib import Path
from typing import List, Dict, NamedTuple, Any, Union, Callable, Awaitable, cast, Mapping

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
    host: str


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

    secretsFile: TPath = None
    remoteGateways: List[RemoteGateway] = []
    localGateway: LocalGateway = LocalGateway()
    defaultPublishLocation: TPath = Path("private/default-publish")
    pinnedPaths: Dict[str, TPath] = {}

    async def get_user_info(self, context: Context) -> UserInfo:

        users_info = parse_json(self.usersInfo)

        if context.config.userEmail in users_info:
            data = users_info[context.config.userEmail]
            # email can be "anonymous" or "default", they link to actual identities,
            # in these cases data is here the linked email, we need to re-evaluate to get the identity
            if isinstance(data, str):
                data = users_info[data]
            return UserInfo(**data)

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


class DeadlinedCache(NamedTuple):

    value: any
    deadline: float
    dependencies: Dict[str, str]

    def is_valid(self, dependencies) -> bool:

        for k, v in self.dependencies.items():
            if k not in dependencies or dependencies[k] != v:
                return False
        margin = self.deadline - datetime.timestamp(datetime.now())
        return margin > 0


class YouwolConfiguration(NamedTuple):

    http_port: int

    userEmail: Union[str, None]

    userConfig: UserConfiguration

    pathsBook: PathsBook

    localClients: LocalClients

    configurationParameters: ConfigParameters = ConfigParameters(parameters={})

    cache: Dict[str, Any] = {}

    tokensCache: List[DeadlinedCache] = []

    async def get_auth_token(self, context: Context):
        username = self.userEmail
        remote_host = self.userConfig.general.remoteGateways[0].host
        dependencies = {"username": username, "host": remote_host, "type": "auth_token"}
        cached_token = next((c for c in self.tokensCache if c.is_valid(dependencies)), None)
        if cached_token:
            return cached_token.value

        secrets = parse_json(self.userConfig.general.secretsFile)
        client_id = secrets[remote_host]['clientId']
        client_secret = secrets[remote_host]['clientSecret']
        pwd = secrets[username]['password']
        access_token = await get_remote_auth_token(
            username=username,
            pwd=pwd,
            client_id=client_id,
            client_secret=client_secret,
            )
        deadline = datetime.timestamp(datetime.now()) + 1 * 60 * 60 * 1000
        self.tokensCache.append(DeadlinedCache(value=access_token, deadline=deadline, dependencies=dependencies))

        await context.info(step=ActionStep.STATUS, content="Access token renewed",
                           json={"access_token": access_token})
        return access_token

    async def get_assets_gateway_client(self, context: Context) -> AssetsGatewayClient:

        remote_host = self.userConfig.general.remoteGateways[0].host
        auth_token = await self.get_auth_token(context=context)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return AssetsGatewayClient(url_base=f"https://{remote_host}/api/assets-gateway", headers=headers)
