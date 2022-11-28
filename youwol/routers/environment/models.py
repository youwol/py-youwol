from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel
from youwol.environment import ErrorResponse, DispatchInfo

from youwol.routers.projects.projects_loader import Result


class CustomDispatch(BaseModel):
    type: str
    name: str
    activated: Optional[bool]
    parameters: Optional[Dict[str, str]]


class CustomDispatchesResponse(BaseModel):
    dispatches: Dict[str, List[DispatchInfo]]


class ProjectsLoadingResults(BaseModel):
    results: List[Result]


class RemoteGatewayInfo(BaseModel):
    host: str
    connected: Optional[bool]


class SwitchConfigurationBody(BaseModel):
    path: List[str]


class SwitchResponse(BaseModel):
    errors: List[ErrorResponse]


class LoginBody(BaseModel):
    userId: Optional[str]
    host: Optional[str]


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
