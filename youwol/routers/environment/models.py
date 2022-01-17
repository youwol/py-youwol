from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from youwol.environment.models_project import ErrorResponse
from youwol.environment.projects_loader import Result


class AvailableProfiles(BaseModel):
    profiles: Optional[List[str]]
    active: str


class ProjectsLoadingResults(BaseModel):
    results: List[Result]


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
    profile: str


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
