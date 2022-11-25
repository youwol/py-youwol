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
    host: str
    openidClient: Union[PublicClient, PrivateClient]
    openidBaseUrl: str
    keycloakAdminBaseUrl: Optional[str]
    adminClient: Optional[PrivateClient]
    users: List[DirectAuthUser] = []

    @classmethod
    def from_config(cls, cloud: YouwolCloud, impersonations: List[Impersonation]):
        return RemoteGateway(
            **cloud.dict(),
            users=[DirectAuthUser(username=user.userName, password=user.password)
                   for user in impersonations if cloud.host in user.forHosts]
        )


def get_standard_youwol_cloud(host: str):
    return YouwolCloud(**default_cloud_environment(host))


class Secret(BaseModel):
    clientId: str
    clientSecret: str


@dataclass(frozen=False)
class ApiConfiguration:
    open_api_prefix: str
    base_path: str

class IPipelineFactory:
    """
    This class should not be used: instead use IPipelineFactory from youwol.environment.models_project.
    It is here for backward compatibility purpose & will disappear soon.
    """
    pass


class Projects(BaseModel):
    finder: Callable[
        [YouwolEnvironment, Context],
        Awaitable[List[ConfigPath]]
    ] = lambda env, _ctx: default_projects_finder(env=env)
    templates: List[ProjectTemplate] = []
    uploadTargets: List[UploadTargets] = []
