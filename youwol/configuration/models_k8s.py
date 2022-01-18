from pathlib import Path
from typing import Callable, List

from pydantic.main import BaseModel

from youwol.environment.models_project import Project
from youwol_utils.context import Context


class DockerRepo(BaseModel):
    name: str
    pullSecret: Path
    imageUrlBuilder: Callable[[Project, Context], str]


class OpenIdConnect(BaseModel):
    host: str  # gc.auth.youwol.com
    authSecret: Path


class Docker(BaseModel):
    repositories: List[DockerRepo]


class K8sCluster(BaseModel):
    configFile: Path
    contextName: str
    proxyPort: int
    host: str
    openIdConnect: OpenIdConnect
    docker: Docker

    def __str__(self):
        return f"""K8s cluster:
- config file: {self.configFile}
- context name: {self.contextName}
- proxy port: {self.proxyPort}
- host: {self.host}
"""
