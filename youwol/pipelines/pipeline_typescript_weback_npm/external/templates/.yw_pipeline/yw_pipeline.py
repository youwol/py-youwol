from youwol.environment import YouwolEnvironment
from youwol.routers.projects import IPipelineFactory, Pipeline
from youwol.pipelines.pipeline_typescript_weback_npm.external import PipelineConfig, pipeline

from youwol_utils.context import Context


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, _env: YouwolEnvironment, ctx: Context) -> Pipeline:
        return await pipeline(PipelineConfig(), ctx)
