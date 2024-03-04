# standard library
from enum import Enum

# typing
from typing import Literal

# third parties
from pydantic import BaseModel

# Youwol application
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
    Response model corresponding to [Authentication](@yw-nav-class:model_remote.Authentication).
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
    Response model corresponding to [CloudEnvironment](@yw-nav-class:CloudEnvironment).
    """

    envId: str
    """
    Environment Id, see [CloudEnvironment.envId](@yw-nav-attr:CloudEnvironment.envId).
    """
    host: str
    """
    Host, see [CloudEnvironment.host](@yw-nav-attr:CloudEnvironment.host).
    """
    authentications: list[AuthenticationResponse]
    """
    Available authentication modes, see
    [CloudEnvironment.authentications](@yw-nav-attr:CloudEnvironment.authentications).
    """


class SwitchConfigurationBody(BaseModel):
    path: list[str]


class SwitchResponse(BaseModel):
    errors: list[ErrorResponse]


class LoginBody(BaseModel):
    authId: str | None
    """
    Id of the authentication, need to be referenced in the configuration file under the
    [CloudEnvironment](@yw-nav-class:youwol.app.environment.models.models_config.CloudEnvironment) section
     for the given `envId`.
    """

    envId: str | None
    """
    Id of the environment, need to be referenced in the configuration file under the
    [CloudEnvironments](@yw-nav-class:youwol.app.environment.models.models_config.CloudEnvironments) section.
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
