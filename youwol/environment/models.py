from abc import ABC, abstractmethod
from dataclasses import dataclass
from pydantic import BaseModel
from typing import List, Dict, Callable, Optional, Union, Any, Awaitable

from youwol.configuration.models_config import ConfigPath, UploadTargets
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models_project import Pipeline, ProjectTemplate
from youwol.environment.projects_loader import default_projects_finder
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
    metadata: Dict[str, str]
    openidClient: Union[PublicClient, PrivateClient]
    openidBaseUrl: str
    adminClient: Optional[PrivateClient]
    keycloakAdminBaseUrl: Optional[str]


class Secret(BaseModel):
    clientId: str
    clientSecret: str


@dataclass(frozen=False)
class ApiConfiguration:
    open_api_prefix: str
    base_path: str


class IPipelineFactory(ABC):

    @abstractmethod
    async def get(self, env: YouwolEnvironment, context: Context) -> Pipeline:
        return NotImplemented


class Events(BaseModel):
    onLoad: Callable[[YouwolEnvironment, Context], Optional[Union[Any, Awaitable[Any]]]] = None


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
