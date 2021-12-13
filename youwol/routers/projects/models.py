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


class PipelineStepStatusResponse(BaseModel):
    projectId: str
    stepId: PipelineStepId
    artifacts: dict[ArtifactId, Path]
    manifest: Optional[Manifest] = None
    status: PipelineStepStatus


class PipelineStatusResponse(BaseModel):
    projectId: str
    steps: List[PipelineStepStatusResponse]
