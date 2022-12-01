from youwol.routers.projects import PipelineStep, FlowId, Project
from youwol_utils import Context, files_check_sum
from .. import __pipeline_version__


class SetupStep(PipelineStep):
    id = 'setup'
    run: str = "yarn auto-gen"

    async def get_fingerprint(self, project: Project, flow_id: FlowId, context: Context):

        async with context.start(action="get_fingerprint") as ctx:
            files = [project.path / 'template.py', project.path / 'package.json']
            checksum = files_check_sum(files)
            await ctx.info(text="Step fingerprint retrieved",
                           data={"checksum": checksum, "__pipeline_version__": __pipeline_version__}
                           )
            return f"pipeline#{__pipeline_version__}_checksum:{checksum}", files
