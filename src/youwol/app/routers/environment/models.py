# standard library
from enum import Enum

# typing
from typing import Literal

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment.browser_cache_store import BrowserCacheItem
from youwol.app.environment.errors_handling import ErrorResponse
from youwol.app.environment.models.flow_switches import DispatchInfo


class UserInfo(BaseModel):
    """
    TODO: needs to be updated, most if these information here does not make sense.
    """

    # id should be the subject of a token , as use everywhere to uniquely identify a user
    id: str
    # There is no 'name' for a user, either there is her first / last name (her civil name) or
    # her login, which is the same as the email
    name: str
    email: str
    # Is empty everywhere in the code …
    memberOf: list[str]


class CustomDispatch(BaseModel):
    type: str
    name: str
    activated: bool | None
    parameters: dict[str, str] | None


class CustomDispatchesResponse(BaseModel):
    dispatches: dict[str, list[DispatchInfo]]


class AuthenticationResponse(BaseModel):
    """
    Response model corresponding to :class:`Authentication <youwol.app.environment.models.model_remote.Authentication>`.
    """

    authId: str
    """
    Authentication's ID.
    """
    type: Literal["BrowserAuth", "DirectAuth"]
    """
    Authentication's type.
    """


class CloudEnvironmentResponse(BaseModel):
    """
    Response model corresponding to
    :class:`CloudEnvironment <youwol.app.environment.models.model_remote.CloudEnvironment>`.
    """

    envId: str
    """
    Environment Id, see
    :attr:`youwol.app.environment.models.model_remote.CloudEnvironment.envId`.
    """
    host: str
    """
    Host, see :attr:`CloudEnvironment.host <youwol.app.environment.models.model_remote.CloudEnvironment.host>`.
    """
    authentications: list[AuthenticationResponse]
    """
    Available authentication modes, see
    :attr:`youwol.app.environment.models.model_remote.CloudEnvironment.authentications`.
    """


class SwitchConfigurationBody(BaseModel):
    """
    Body model of the endpoint :func:``POST:/admin/environment/configuration/switch` <switch_configuration>`.
    """

    url: str
    """
    URL pointing to the configuration content.
    """


class SwitchResponse(BaseModel):
    errors: list[ErrorResponse]


class LoginBody(BaseModel):
    """
    Body model of the endpoint :func:``POST:/admin/environment/login` <router.login>`.
    """

    authId: str | None
    """
    Id of the authentication, need to be referenced in the configuration file under the
    :class:`CloudEnvironment <youwol.app.environment.models.model_remote.CloudEnvironment>` section
     for the given `envId`.
    """

    envId: str | None
    """
    Id of the environment, need to be referenced in the configuration file under the
    :class:`CloudEnvironments <youwol.app.environment.models.model_remote.CloudEnvironments>` section.
    """


class SelectRemoteBody(BaseModel):
    name: str


class SyncUserBody(BaseModel):
    email: str
    password: str
    remoteEnvironment: str


class ComponentsUpdateStatus(Enum):
    PENDING = "PENDING"
    SYNC = "SYNC"
    OUTDATED = "OUTDATED"


class ComponentUpdate(BaseModel):
    name: str
    localVersion: str
    latestVersion: str
    status: ComponentsUpdateStatus


class ComponentsUpdate(BaseModel):
    components: list[ComponentUpdate]
    status: ComponentsUpdateStatus


class SyncComponentBody(BaseModel):
    name: str
    version: str


class BrowserCacheStatusResponse(BaseModel):
    """
    Response model of the endpoint :func:``DELETE:/admin/environment/browser-cache` <router.clear_browser_cache>`.
    """

    sessionKey: str
    """
    The session key for the cache, see
    :class:`BrowserCache documentation <youwol.app.environment.models.models_config.BrowserCache>`.
    """

    file: str | None
    """
    The file path supporting the cache
    (if :attr:`BrowserCache.mode <youwol.app.environment.models.models_config.BrowserCache.mode>` is `disk`)
    """

    items: list[BrowserCacheItem]
    """
    The list of items.
    """


class ClearBrowserCacheBody(BaseModel):
    """
    Body model of the endpoint :func:``DELETE:/admin/environment/browser-cache` <router.clear_browser_cache>`.
    """

    memory: bool = True
    """
    Whether to clear `in-memory` items.
    """

    file: bool = False
    """
    Whether to delete associated file on disk (applicable only if
    :attr:`BrowserCache.mode <youwol.app.environment.models.models_config.BrowserCache.mode>` is `disk`).
    """


class ClearBrowserCacheResponse(BaseModel):
    """
    Response model of the endpoint :func:``DELETE:/admin/environment/browser-cache` <router.clear_browser_cache>`.
    """

    deleted: int
    """
    Number of entries deleted.
    """
