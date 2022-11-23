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


class DirectAuthUser(BaseModel):
    username: str
    password: str


class RemoteConfig(BaseModel):
    host: str
    name: Optional[str]
    openidBaseUrl: Optional[str]
    openidClient: Optional[Union[PublicClient, PrivateClient]]
    keycloakAdminBaseURl: Optional[str]
    keycloakAdminClient: Optional[PrivateClient]
    defaultUser: Optional[str]
    directAuthUsers: List[DirectAuthUser] = []

    @staticmethod
    def build(host: str, name: Optional[str] = None, openid_base_url: Optional[str] = None,
              openid_client: Optional[Union[PublicClient, PrivateClient]] = None,
              keycloak_admin_base_url: Optional[str] = None, keycloak_admin_client: Optional[PrivateClient] = None,
              default_user: Optional[str] = None, direct_auth_users: List[DirectAuthUser] = None):
        if default_user and len([user for user in direct_auth_users if user.username == default_user]) == 0:
            raise RuntimeError(f"default user {default_user} for remote {name} is not in directAuthUsers")
        return RemoteConfig(
            host=host,
            name=name if name else host,
            openidBaseUrl=openid_base_url if openid_base_url else f"https://{host}/auth/realms/youwol",
            openidClient=openid_client if openid_client else PublicClient(client_id=default_openid_client_id),
            keycloakAdminBaseURl=keycloak_admin_base_url,
            keycloakAdminClient=keycloak_admin_client,
            directAuthUsers=direct_auth_users if direct_auth_users else [],
            defaultUser=default_user
        )

    def __hash__(self):
        return hash(tuple([self.name,
                           self.host,
                           self.openidBaseUrl,
                           self.openidClient.client_id,
                           self.keycloakAdminBaseURl,
                           self.keycloakAdminClient.client_id if self.keycloakAdminClient else None
                           ]))


class Configuration(BaseModel):
    httpPort: Optional[int]
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
