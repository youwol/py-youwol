from pathlib import Path
from typing import Callable, List

from pydantic.main import BaseModel

from youwol.environment.models_project import Project
from youwol_utils.context import Context


class DeploymentTarget(BaseModel):
    name: str


class Deployment(BaseModel):
    targets: List[DeploymentTarget]


class DockerRepo(DeploymentTarget):
    name: str
    pullSecret: Path
    imageUrlBuilder: Callable[[Project, Context], str]


class Docker(Deployment):
    repositories: List[DockerRepo] = []
    targets: List[DeploymentTarget] = []

    def get_repo(self, repo_name: str):
        return next(repo for repo in self.repositories if repo.name == repo_name)


class K8sCluster(BaseModel):
    configFile: Path
    contextName: str
    proxyPort: int
    docker: Docker

    def __str__(self):
        return f"""K8s cluster:
- config file: {self.configFile}
- context name: {self.contextName}
- proxy port: {self.proxyPort}
"""


class K8sTarget(DeploymentTarget):
    name: str
    context: str


class K8s(Deployment):
    configFile: Path
    targets: List[K8sTarget]
    proxyPort: int


class YwPlatformTarget(DeploymentTarget):
    name: str
    host: str


class YouWolCDN(Deployment):
    targets: List[YwPlatformTarget]

