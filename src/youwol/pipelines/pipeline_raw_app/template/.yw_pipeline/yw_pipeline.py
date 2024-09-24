# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.projects import (
    BrowserAppBundle,
    BrowserAppGraphics,
    Execution,
    IPipelineFactory,
)

# Youwol utilities
from youwol.utils.context import Context

# Youwol pipelines
from youwol.pipelines.pipeline_raw_app import PipelineConfig, pipeline


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, _env: YouwolEnvironment, context: Context):

        graphics = BrowserAppGraphics(appIcon={"class": "far fa-laugh-beam fa-2x"})
        config = PipelineConfig(
            target=BrowserAppBundle(
                displayName="{{application_name}}",
                execution=Execution(standalone=True),
                graphics=graphics,
            )
        )
        return await pipeline(config, context)
