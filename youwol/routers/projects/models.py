from pathlib import Path
from typing import List, Any, Optional

from pydantic import BaseModel
from youwol.configuration import PipelineStepStatus

ArtifactId = str
PipelineStepId = str


class Manifest(BaseModel):
    succeeded: bool
    fingerprint: str
    creationDate: str
    files: List[str]
    cmdOutputs: List[str] = []


class ArtifactResponse(BaseModel):
    id: str
    path: Path

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
