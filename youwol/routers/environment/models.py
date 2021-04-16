from typing import List, Dict, Any

from pydantic import BaseModel

from youwol.configuration.models_base import ErrorResponse, ConfigParameters
from youwol.configuration.user_configuration import UserInfo, UserConfiguration


class StatusResponse(BaseModel):
    configurationPath: str
    configurationParameters: ConfigParameters
    configuration: UserConfiguration
    users: List[str]
    userInfo: UserInfo


class SwitchConfigurationBody(BaseModel):
    path: str


class SwitchResponse(BaseModel):
    errors: List[ErrorResponse]


class LoginBody(BaseModel):
    email: str


class PostParametersBody(BaseModel):
    values: Dict[str, Any]


class SyncUserBody(BaseModel):
    email: str
    password: str
    remoteEnvironment: str
