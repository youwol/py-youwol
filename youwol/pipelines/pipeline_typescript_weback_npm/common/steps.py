from typing import Optional

from youwol.routers.projects.models_project import PipelineStep, Project, Manifest, PipelineStepStatus
from youwol_utils.context import Context


class InitStep(PipelineStep):
    id: str = 'init'
    run: str = 'yarn'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        if (project.path / 'node_modules').exists():
            return PipelineStepStatus.OK
        return PipelineStepStatus.none
