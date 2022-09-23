import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Callable, Optional, Union, Any, Awaitable

from pydantic import BaseModel

from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models_project import Pipeline
from youwol_utils.clients.oidc.oidc_config import PrivateClient, PublicClient
from youwol_utils.context import Context


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    memberOf: List[str]


class RemoteGateway(BaseModel):
    name: str
    host: str
    metadata: Dict[str, str]
    openidClient: Union[PublicClient, PrivateClient]
    openidBaseUrl: str
    adminClient: Optional[PrivateClient]
    keycloakAdminBaseUrl: Optional[str]


class Secret(BaseModel):
    clientId: str
    clientSecret: str


@dataclass(frozen=False)
class ApiConfiguration:
    open_api_prefix: str
    base_path: str


class IPipelineFactory(ABC):

    @abstractmethod
    async def get(self, env: YouwolEnvironment, context: Context) -> Pipeline:
        return NotImplemented


class Events(BaseModel):
    onLoad: Callable[[YouwolEnvironment, Context], Optional[Union[Any, Awaitable[Any]]]] = None


class IConfigurationCustomizer(ABC):

    @abstractmethod
    async def customize(self, _youwol_configuration: YouwolEnvironment) -> YouwolEnvironment:
        return NotImplemented


class K8sNodeInfo(BaseModel):
    cpu: str
    memory: str
    architecture: str
    kernelVersion: str
    operating_system: str
    os_image: str

    def __str__(self):
        return f"""
cpu: {self.cpu}, memory: {self.memory}, architecture: {self.architecture}, 'os': {self.operating_system}"""


class K8sInstanceInfo(BaseModel):
    access_token: str
    nodes: List[K8sNodeInfo]
    # api_gateway_ip: Optional[str]
    k8s_api_proxy: str

    def __str__(self):
        nodes_info = functools.reduce(lambda acc, e: acc + e, [n.__str__() for n in self.nodes], "")
        main = "/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#/pod?namespace=_all"
        return f"""k8s instance info:
- API proxy url: {self.k8s_api_proxy}
- dashboard: {self.k8s_api_proxy}{main}
- access_token: {self.access_token}
- {len(self.nodes)} nodes: {nodes_info}
"""
