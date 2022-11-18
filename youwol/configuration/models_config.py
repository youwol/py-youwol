from enum import Enum
from pathlib import Path
from typing import List, Union, Optional, Dict, Callable, Awaitable, Any

from pydantic import BaseModel

from youwol.configuration.defaults import default_openid_client_id
from youwol.configuration.models_config_middleware import CustomMiddleware
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models_project import ProjectTemplate
from youwol.middlewares.models_dispatch import AbstractDispatch, RedirectDispatch
from youwol.routers.custom_commands.models import Command
from youwol_utils import Context
from youwol_utils.clients.oidc.oidc_config import PublicClient, PrivateClient
from youwol_utils.servers.fast_api import FastApiRouter


class Events(BaseModel):
    onLoad: Callable[[YouwolEnvironment, Context], Optional[Union[Any, Awaitable[Any]]]] = None


class PortRange(BaseModel):
    start: int
    end: int


ConfigPath = Union[str, Path]


class ModuleLoading(BaseModel):
    path: Optional[ConfigPath]
    name: str

    def __str__(self):
        return f"{self.path}#{self.name}"


class CdnOverride(BaseModel):
    packageName: str
    port: Optional[int]


class Redirection(BaseModel):
    from_url_path: str
    to_url: str


class JwtSource(str, Enum):
    COOKIE = 'cookie'
    CONFIG = 'config'


class UploadTarget(BaseModel):
    name: str


class UploadTargets(BaseModel):
    targets: List[UploadTarget]


class Projects(BaseModel):
    finder: Union[
        ConfigPath,
        List[ConfigPath],
        Callable[[YouwolEnvironment, Context], List[ConfigPath]],
        Callable[[YouwolEnvironment, Context], Awaitable[List[ConfigPath]]],
        ModuleLoading
    ] = None
    templates: List[ProjectTemplate] = []
    uploadTargets: List[UploadTargets] = []


class RemoteConfig(BaseModel):
    name: Optional[str]
    host: str
    openidBaseUrl: Optional[str]
    openidClient: Optional[Union[PublicClient, PrivateClient]]
    keycloakAdminBaseURl: Optional[str]
    keycloakAdminClient: Optional[PrivateClient]

    def __hash__(self):
        return hash(tuple([self.host, self.openidBaseUrl, self.openidClient.client_id]))

    @classmethod
    def default_for_host(cls, host: str):
        return RemoteConfig(
            host=host,
            openidBaseUrl=f"https://{host}/auth/realms/youwol",
            openidClient=PublicClient(client_id=default_openid_client_id)
        )


class Configuration(BaseModel):
    httpPort: Optional[int]
    jwtSource: Optional[JwtSource]
    selectedRemote: Optional[Union[str, RemoteConfig]]
    remotes: List[RemoteConfig] = []
    redirectBasePath: Optional[str]
    user: Optional[str]
    portsBook: Optional[Dict[str, int]]
    routers: Optional[List[FastApiRouter]]
    projects: Optional[Projects]
    configDir: Optional[ConfigPath]
    dataDir: Optional[ConfigPath]
    cacheDir: Optional[ConfigPath]
    serversPortsRange: Optional[PortRange]
    cdnAutoUpdate: Optional[bool]
    middlewares: Optional[List[CustomMiddleware]]
    dispatches: Optional[List[Union[str, Redirection, CdnOverride, AbstractDispatch, RedirectDispatch]]]
    defaultModulePath: Optional[ConfigPath]
    additionalPythonSrcPath: Optional[Union[ConfigPath, List[ConfigPath]]]
    events: Optional[Union[Events, str, ModuleLoading]]
    customCommands: List[Union[str, Command, ModuleLoading]] = []
    customize: Optional[Union[str, ModuleLoading]]
