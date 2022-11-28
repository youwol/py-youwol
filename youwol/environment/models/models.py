import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import List, Callable, Optional, Union, Awaitable, cast

from pydantic import BaseModel
from youwol.environment.models.models_config import default_cloud_environment, ConfigPath, YouwolCloud,\
    Impersonation, Projects as ProjectsConfig, ProjectTemplate, PathsBook

from youwol.environment.projects_finders import default_projects_finder
from youwol_utils.clients.oidc.oidc_config import PrivateClient, PublicClient
from youwol_utils.context import Context


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    memberOf: List[str]


class DirectAuthUser(BaseModel):
    username: str
    password: str


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
        [PathsBook, Context],
        Awaitable[List[ConfigPath]]
    ]

    templates: List[ProjectTemplate]

    @classmethod
    def from_config(cls, projects: ProjectsConfig):

        finder = None
        if callable(projects.finder):
            # finder is Callable[[YouwolEnvironment, Context], List[ConfigPath]]
            # or Callable[[YouwolEnvironment, Context], Awaitable[List[ConfigPath]]]
            is_coroutine = inspect.iscoroutinefunction(projects.finder)

            async def await_finder(env, ctx):
                #  if no cast => python complains about typing w/ ModuleLoading accepting only keyword arguments
                return cast(Callable[[PathsBook, Context], List[ConfigPath]], projects.finder)(env, ctx)

            finder = projects.finder if is_coroutine else await_finder
        elif isinstance(projects.finder, str) \
                or isinstance(projects.finder, Path) \
                or isinstance(projects.finder, List):
            # finder is List[ConfigPath]
            async def default_finder(paths_book, _ctx):
                return default_projects_finder(paths_book=paths_book, root_folders=projects.finder)

            finder = default_finder

        return Projects(
            finder=finder,
            templates=projects.templates
        )

