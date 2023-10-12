# standard library
from enum import Enum

# typing
from typing import Dict, List, Optional

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment.errors_handling import ErrorResponse
from youwol.app.environment.models.models_config import DispatchInfo


class UserInfo(BaseModel):
    """Most of these informations does not make sense …"""

    # id should be the subject of a token , as use everywhere to uniquely identify an user
    id: str
    # There is no 'name' for an user, either there is her first / last name (her civil name) or
    # her login, which is the same as the email
    name: str
    email: str
    # Is empty everywhere in the code …
    memberOf: List[str]


class CustomDispatch(BaseModel):
    type: str
    name: str
    activated: Optional[bool]
    parameters: Optional[Dict[str, str]]


class CustomDispatchesResponse(BaseModel):
    dispatches: Dict[str, List[DispatchInfo]]


class RemoteGatewayInfo(BaseModel):
    host: str
    connected: Optional[bool]


class SwitchConfigurationBody(BaseModel):
    path: List[str]


class SwitchResponse(BaseModel):
    errors: List[ErrorResponse]


class LoginBody(BaseModel):
    authId: Optional[str]
    envId: Optional[str]


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
    components: List[ComponentUpdate]
    status: ComponentsUpdateStatus


class SyncComponentBody(BaseModel):
    name: str
    version: str
