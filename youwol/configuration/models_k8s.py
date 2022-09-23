from pathlib import Path
from typing import Callable, List, Optional

from pydantic.main import BaseModel

from youwol.environment.models_project import Project
from youwol_utils.context import Context


class UploadTarget(BaseModel):
    name: str


class UploadTargets(BaseModel):
    targets: List[UploadTarget]


class DockerRepo(UploadTarget):
    name: str
    imageUrlBuilder: Optional[Callable[[Project, Context], str]]
    host: str

    def get_project_url(self, project: Project, context: Context):
        return self.imageUrlBuilder(project, context) if self.imageUrlBuilder else f"{self.host}/{project.name}"


class DockerImagesPush(UploadTargets):
    targets: List[DockerRepo] = []

    def get_repo(self, repo_name: str):
        return next(repo for repo in self.targets if repo.name == repo_name)


class K8sCluster(BaseModel):
    configFile: Path
    contextName: str
    proxyPort: int
    docker: DockerImagesPush

    def __str__(self):
        return f"""K8s cluster:
- config file: {self.configFile}
- context name: {self.contextName}
- proxy port: {self.proxyPort}
"""


class K8sClusterTarget(UploadTarget):
    name: str
    context: str


class HelmChartsInstall(UploadTargets):
    k8sConfigFile: Path
    targets: List[K8sClusterTarget]


class YwPlatformTarget(UploadTarget):
    name: str
    host: str


class YwCdnPackagesPublish(UploadTargets):
    targets: List[YwPlatformTarget]


class PipelinesSourceInfo(BaseModel):
    uploadTargets: List[UploadTargets]
    