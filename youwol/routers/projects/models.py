from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from configuration import Manifest
from youwol.configuration import PipelineStepStatus

ArtifactId = str
PipelineStepId = str


class ArtifactResponse(BaseModel):
    id: str
    path: Path
    openingUrl: Optional[str]


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
