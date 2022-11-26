from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Mapping

from pydantic import BaseModel

from youwol.routers.projects.models_project import PipelineStepStatus, Manifest, Link, Project

ArtifactId = str
PipelineStepId = str


class ListProjectsResponse(BaseModel):
    projects: List[Project]


class ArtifactResponse(BaseModel):
    id: str
    path: Path
    links: List[Link] = []


class ArtifactsResponse(BaseModel):
    artifacts: List[ArtifactResponse]


class PipelineStepStatusResponse(BaseModel):
    projectId: str
    flowId: str
    stepId: PipelineStepId
    artifactFolder: Path
    artifacts: List[ArtifactResponse]
    manifest: Optional[Manifest] = None
    status: PipelineStepStatus


class PipelineStatusResponse(BaseModel):
    projectId: str
    steps: List[PipelineStepStatusResponse]


class ChildToParentConnections(BaseModel):
    id: str
    parentIds: List[str]


class DependenciesResponse(BaseModel):
    above: List[str]
    below: List[str]
    dag: List[ChildToParentConnections]
    simpleDag: List[ChildToParentConnections]


class ProjectStatusResponse(BaseModel):
    projectId: str
    projectName: str
    workspaceDependencies: DependenciesResponse


class CdnVersionResponse(BaseModel):
    name: str
    version: str
    versionNumber: int
    filesCount: int
    bundleSize: int
    path: Path
    namespace: str


class CdnResponse(BaseModel):
    name: str
    versions: List[CdnVersionResponse]


class Event(Enum):
    runStarted = 'runStarted'
    runDone = 'runDone'
    statusCheckStarted = 'statusCheckStarted'


class PipelineStepEvent(BaseModel):
    projectId: str
    flowId: str
    stepId: str
    event: Event


class CreateProjectFromTemplateBody(BaseModel):
    type: str
    parameters: Dict[str, str]


class CreateProjectFromTemplateResponse(Project):
    pass


class UpdateConfigurationResponse(BaseModel):
    path: Path
    configuration: Mapping[str, Any]
