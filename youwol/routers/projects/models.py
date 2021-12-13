from pathlib import Path
from typing import List

from pydantic import BaseModel
from youwol.configuration import PipelineStepStatus

ArtifactId = str
PipelineStepId = str


class PipelineStepStatusResponse(BaseModel):
    projectId: str
    stepId: PipelineStepId
    artifacts: dict[ArtifactId, Path]
    status: PipelineStepStatus
