from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable, Optional, Union, Awaitable

from pydantic import BaseModel
from youwol.configuration.models_config import ConfigPath, UploadTargets, RemoteConfig, DirectAuthUser
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models_project import Pipeline, ProjectTemplate
from youwol.environment.utils import default_projects_finder
from youwol_utils.clients.oidc.oidc_config import PrivateClient, PublicClient
from youwol_utils.context import Context


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    memberOf: List[str]


class RemoteGateway(BaseModel):
    name: str
    host: str
    openidClient: Union[PublicClient, PrivateClient]
    openidBaseUrl: str
    keycloakAdminBaseUrl: Optional[str]
    adminClient: Optional[PrivateClient]
    users: List[DirectAuthUser] = []

    @classmethod
    def from_config(cls, remote_config: RemoteConfig):
        return RemoteGateway(
            name=remote_config.name if remote_config.name else remote_config.host,
            host=remote_config.host,
            openidClient=remote_config.openidClient,
            openidBaseUrl=remote_config.openidBaseUrl,
            keycloakAdminBaseUrl=remote_config.keycloakAdminBaseURl,
            adminClient=remote_config.keycloakAdminClient,
            users=remote_config.directAuthUsers
        )


class Secret(BaseModel):
    clientId: str
    clientSecret: str


@dataclass(frozen=False)
class ApiConfiguration:
    open_api_prefix: str
    base_path: str


class IPipelineFactory(ABC):

    @abstractmethod
    async def get(self, _env: YouwolEnvironment, _context: Context) -> Pipeline:
        return NotImplemented


class IConfigurationCustomizer(ABC):

    @abstractmethod
    async def customize(self, _youwol_configuration: YouwolEnvironment) -> YouwolEnvironment:
        return NotImplemented


class Projects(BaseModel):
    finder: Callable[
        [YouwolEnvironment, Context],
        Awaitable[List[ConfigPath]]
    ] = lambda env, _ctx: default_projects_finder(env=env)
    templates: List[ProjectTemplate] = []
    uploadTargets: List[UploadTargets] = []
