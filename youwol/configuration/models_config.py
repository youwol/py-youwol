from pathlib import Path
from typing import List, Union, Optional, Callable, Awaitable, Any

from pydantic import BaseModel
from youwol.configuration.defaults import default_openid_client_id, default_path_cache_dir, \
    default_path_data_dir, default_http_port
from youwol.configuration.models_config_middleware import CustomMiddleware
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models_project import ProjectTemplate
from youwol.routers.custom_commands.models import Command
from youwol_utils import Context
from youwol_utils.clients.oidc.oidc_config import PublicClient, PrivateClient
from youwol_utils.servers.fast_api import FastApiRouter


class Events(BaseModel):
    onLoad: Callable[[YouwolEnvironment, Context], Optional[Union[Any, Awaitable[Any]]]] = None


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


class Projects(BaseModel):
    finder: Union[
        ConfigPath,
        List[ConfigPath],
        Callable[[YouwolEnvironment, Context], List[ConfigPath]],
        Callable[[YouwolEnvironment, Context], Awaitable[List[ConfigPath]]]
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


class System(BaseModel):
    httpPort: Optional[int] = default_http_port
    selectedRemote: Optional[Union[str, RemoteConfig]]
    remotes: Optional[List[RemoteConfig]]
    configDir: Optional[ConfigPath]
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
