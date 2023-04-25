from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.projects import IPipelineFactory, Pipeline
from youwol.app.pipelines.pipeline_typescript_weback_npm.external import PipelineConfig, pipeline

from youwol.utils.context import Context


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, _env: YouwolEnvironment, ctx: Context) -> Pipeline:
        return await pipeline(PipelineConfig(), ctx)
