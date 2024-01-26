"""
The purpose of this pipeline is to package and publish a raw javascript + HTML project.
To use this pipeline, prerequisites are:

*  have a folder that contains a `package.json` file that includes:
    *  the name & version of the package
    *  the path to the entry point (the `index.html` file)
*  have a valid `index.html` file, eventually referencing javascript files

A typical example of `yw_pipeline.py` file is:

```python
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.projects import IPipelineFactory, BrowserAppBundle, Execution, BrowserAppGraphics
from youwol.pipelines.pipeline_raw_app import pipeline, PipelineConfig
from youwol.utils.context import Context


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, _env: YouwolEnvironment, context: Context):
        config = PipelineConfig(
            target=BrowserAppBundle(
                displayName="My application",
                execution=Execution(standalone=True),
                graphics=BrowserAppGraphics(appIcon={'class': 'far fa-laugh-beam fa-2x'})
            )
        )
        return await pipeline(config, context)
```

Additional options regarding packaging can be defined within
[PipelineConfig](@yw-nav-class:youwol.pipelines.pipeline_raw_app.PipelineConfig).

The pipeline is globally configured by default to publish in the remote CDN `platform.youwol.com` using
[browser based authentication](@yw-nav-class:youwol.app.environment.models.models_config.BrowserAuth).
Refer to the function [set_environment](@yw-nav-function:youwol.pipelines.pipeline_raw_app.set_environment) to specify
other targets.

"""

# relative
from .pipeline import *
