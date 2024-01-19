# standard library
from collections.abc import Mapping
from enum import Enum
from pathlib import Path

# typing
from typing import Any, Optional

# third parties
from pydantic import BaseModel

# relative
from .models_project import Link, Manifest, PipelineStepStatus, Project

ArtifactId = str
PipelineStepId = str


class Failure(BaseModel):
    path: Path
    failure: str = "generic"
    message: str


class FailurePipelineNotFound(Failure):
    failure: str = "pipeline_not_found"
    message: str = "Pipeline not found"


class FailureDirectoryNotFound(Failure):
    failure: str = "directory_not_found"
    message: str = "Project's directory not found"


class FailureImportException(Failure):
    failure: str = "import"
    traceback: str
    exceptionType: str


class ListProjectsResponse(BaseModel):
    projects: list[Project]


class ArtifactResponse(BaseModel):
    id: str
    path: Path
    links: list[Link] = []


class ArtifactsResponse(BaseModel):
    artifacts: list[ArtifactResponse]


class PipelineStepStatusResponse(BaseModel):
    projectId: str
    flowId: str
    stepId: PipelineStepId
    artifactFolder: Path
    artifacts: list[ArtifactResponse]
    manifest: Optional[Manifest] = None
    status: PipelineStepStatus


class PipelineStatusResponse(BaseModel):
    projectId: str
    steps: list[PipelineStepStatusResponse]


class ChildToParentConnections(BaseModel):
    id: str
    parentIds: list[str]


class DependenciesResponse(BaseModel):
    above: list[str]
    below: list[str]
    dag: list[ChildToParentConnections]
    simpleDag: list[ChildToParentConnections]


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
    versions: list[CdnVersionResponse]


class Event(Enum):
    runStarted = "runStarted"
    runDone = "runDone"
    statusCheckStarted = "statusCheckStarted"


class PipelineStepEvent(BaseModel):
    projectId: str
    flowId: str
    stepId: str
    event: Event


class CreateProjectFromTemplateBody(BaseModel):
    type: str
    parameters: dict[str, str]


class UpdateConfigurationResponse(BaseModel):
    path: Path
    configuration: Mapping[str, Any]
