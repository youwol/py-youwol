from enum import Enum
from typing import List, Dict, Any, Optional

from pydantic import BaseModel

from configuration import YouwolConfiguration
from youwol.configuration.models_base import ErrorResponse
from youwol.configuration.user_configuration import UserInfo


class RemoteGatewayInfo(BaseModel):
    name: str
    host: str
    connected: Optional[bool]


class SwitchConfigurationBody(BaseModel):
    path: List[str]


class SwitchResponse(BaseModel):
    errors: List[ErrorResponse]


class LoginBody(BaseModel):
    email: Optional[str]


class SelectRemoteBody(BaseModel):
    name: str


class PostParametersBody(BaseModel):
    values: Dict[str, Any]


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
