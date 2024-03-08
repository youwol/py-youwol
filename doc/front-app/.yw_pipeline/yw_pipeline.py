# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.projects import (
    BrowserApp,
    BrowserAppGraphics,
    Execution,
    IPipelineFactory,
    Link,
)

# Youwol utilities
from youwol.utils.context import Context

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm import (
    PipelineConfig,
    PublishConfig,
    pipeline,
)


class PipelineFactory(IPipelineFactory):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, _env: YouwolEnvironment, context: Context):
        config = PipelineConfig(
            target=BrowserApp(
                displayName="py-youwol-doc",
                execution=Execution(standalone=True),
                graphics=BrowserAppGraphics(
                    appIcon={"class": "far fa-laugh-beam fa-2x"}, fileIcon={}
                ),
                links=[
                    Link(name="doc", url="dist/docs/index.html"),
                    Link(name="coverage", url="coverage/lcov-report/index.html"),
                    Link(name="bundle-analysis", url="dist/bundle-analysis.html"),
                ],
            ),
            publishConfig=PublishConfig(packagedFolders=["assets"]),
        )
        return await pipeline(config, context)
