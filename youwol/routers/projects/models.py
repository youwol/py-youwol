from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from youwol.configuration import PipelineStepStatus, Manifest, Link

ArtifactId = str
PipelineStepId = str


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
