from pathlib import Path
from typing import List, Union, Optional, Callable, Awaitable, Any, Dict, Tuple

from pydantic import BaseModel
from youwol.configuration.defaults import default_path_cache_dir, \
    default_path_data_dir, default_http_port, default_platform_host, default_cloud_environment
from youwol.configuration.models_config_middleware import CustomMiddleware
from youwol.environment.paths import PathsBook
from youwol.environment.utils import default_projects_finder
from youwol.routers.custom_commands.models import Command
from youwol_utils import Context
from youwol_utils.clients.oidc.oidc_config import PublicClient, PrivateClient
from youwol_utils.servers.fast_api import FastApiRouter


class Events(BaseModel):
    onLoad: Callable[[Context], Optional[Union[Any, Awaitable[Any]]]] = None


ConfigPath = Union[str, Path]


class CdnOverride(BaseModel):
    packageName: str
    port: Optional[int]


class Redirection(BaseModel):
    from_url_path: str
    to_url: str


class UploadTarget(BaseModel):
    name: str


class UploadTargets(BaseModel):
    targets: List[UploadTarget]


class ProjectTemplate(BaseModel):
    icon: Any
    type: str
    folder: Union[str, Path]
    parameters: Dict[str, str]
    generator: Callable[[Path, Dict[str, str], Context], Awaitable[Tuple[str, Path]]]


class Projects(BaseModel):
    finder: Union[
        ConfigPath,
        List[ConfigPath],
        Callable[[PathsBook, Context], List[ConfigPath]],
        Callable[[PathsBook, Context], Awaitable[List[ConfigPath]]]
    ] = lambda paths_book, _ctx: default_projects_finder(paths_book=paths_book)
    templates: List[ProjectTemplate] = []
    uploadTargets: List[UploadTargets] = []


class DirectAuthUser(BaseModel):
    username: str
    password: str


class YouwolCloud(BaseModel):
    host: str
    name: str
    openidBaseUrl: str
    openidClient: Union[PublicClient, PrivateClient]
    keycloakAdminBaseUrl: str
    keycloakAdminClient: Optional[PrivateClient] = None


class RemoteAccess(BaseModel):
    host: str
    userId: Optional[str]


class BrowserAuthAccess(RemoteAccess):
    host: str


class ImpersonateAuthAccess(RemoteAccess):
    host: str
    userId: str


class Impersonation(BaseModel):
    userId: str
    userName: str
    password: str
    forHosts: List[str] = []


class CloudEnvironments(BaseModel):
    defaultAccess: RemoteAccess = BrowserAuthAccess(host=default_platform_host)
    environments: List[YouwolCloud] = []
    impersonations: List[Impersonation] = []


class System(BaseModel):
    httpPort: Optional[int] = default_http_port
    cloudEnvironments: CloudEnvironments = CloudEnvironments(
        environments=[YouwolCloud(**default_cloud_environment(default_platform_host))]
    )
    dataDir: Optional[ConfigPath] = default_path_data_dir
    cacheDir: Optional[ConfigPath] = default_path_cache_dir


class CustomEndPoints(BaseModel):
    commands: Optional[List[Command]] = []
    routers: Optional[List[FastApiRouter]] = []


class Customization(BaseModel):
    endPoints: CustomEndPoints = CustomEndPoints()
    middlewares: Optional[List[CustomMiddleware]] = []
    events: Optional[Events] = Events()


class Configuration(BaseModel):
    system: Optional[System] = System()
    projects: Optional[Projects] = Projects()
    customization: Optional[Customization] = Customization()
