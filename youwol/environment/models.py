from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Callable, Optional, Union, Any, Awaitable

from pydantic import BaseModel

from youwol.environment.models_project import Pipeline
from youwol.context import Context
from youwol.environment.forward_declaration import YouwolEnvironment


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    memberOf: List[str]


class RemoteGateway(BaseModel):
    name: str
    host: str
    metadata: Dict[str, str]


class Secret(BaseModel):
    clientId: str
    clientSecret: str


@dataclass(frozen=False)
class ApiConfiguration:
    open_api_prefix: str
    base_path: str


class IPipelineFactory(ABC):

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    async def get(self) -> Pipeline:
        return NotImplemented


class Events(BaseModel):
    onLoad: Callable[[YouwolEnvironment, Context], Optional[Union[Any, Awaitable[Any]]]] = None


class IConfigurationCustomizer(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def customize(self, _youwol_configuration: YouwolEnvironment) -> YouwolEnvironment:
        return NotImplemented
