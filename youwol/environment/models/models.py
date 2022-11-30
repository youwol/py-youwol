import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import List, Callable, Awaitable, cast, Optional

from pydantic import BaseModel
from youwol.environment.models.defaults import default_auth_provider, default_platform_host
from youwol.environment.models.models_config import ConfigPath, Projects as ProjectsConfig, \
    ProjectTemplate, PathsBook, AuthorizationProvider, CloudEnvironment, BrowserAuth, Authentication

from youwol.environment.projects_finders import default_projects_finder
from youwol_utils.context import Context


def get_standard_auth_provider(host: str, **kwargs) -> AuthorizationProvider:
    """
    Configuration for a standard YouWol installation.

    :param host: host of the installation (e.g. platform.youwol.com)
    :return: The configuration
    """
    return AuthorizationProvider(**{**default_auth_provider(host), **kwargs})


def get_standard_youwol_env(
        env_id: str,
        host: Optional[str] = None,
        authentications: Optional[List[Authentication]] = None,
        **kwargs
) -> CloudEnvironment:
    host = host or default_platform_host
    authentications = authentications or [BrowserAuth(authId='browser')]
    return CloudEnvironment(
        envId=env_id,
        host=host,
        authProvider=get_standard_auth_provider("platform.youwol.com", **kwargs),
        authentications=authentications
    )


@dataclass(frozen=True)
class ApiConfiguration:
    open_api_prefix: str
    base_path: str


class IPipelineFactory:
    """
    This class should not be used: instead use IPipelineFactory from youwol.environment.models_project.
    It is here for backward compatibility purpose & will disappear soon.
    """
    pass


class ProjectsSanitized(BaseModel):

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

        return ProjectsSanitized(
            finder=finder,
            templates=projects.templates
        )
