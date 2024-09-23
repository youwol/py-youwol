"""
## Presentation

The purpose of this pipeline is to package and publish a JavaScript web application.

### Steps Involved

The build process for this application is left to the user.
This pipeline's sole responsibility is to package and publish the project, the steps involved are:

*  :class:`PackageStep <youwol.pipelines.pipeline_raw_app.pipeline.PackageStep>`: Generates a `package` artifact,
including a configurable set of files from the project.
See :class:`PackageConfig <youwol.pipelines.pipeline_raw_app.pipeline.PackageConfig>`.
*  :class:`PublishCdnLocalStep <youwol.pipelines.publish_cdn.PublishCdnLocalStep>`: Publish the `package` artifact in
 the local components database.
*  :class:`PublishCdnRemoteStep <youwol.pipelines.publish_cdn.PublishCdnRemoteStep>`: Publish the `package` artifact in
 the remote(s) components database.

Refer to the :class:`PipelineConfig <youwol.pipelines.pipeline_raw_app.pipeline.PipelineConfig>` regarding
configuration.

<note level="hint">
The pipeline is pre-configured by default to publish on the remote CDN `platform.youwol.com` using
:class:`browser based authentication <youwol.app.environment.models.model_remote.BrowserAuth>`.
You can use the function :func:`set_environment <youwol.pipelines.pipeline_raw_app.pipeline.set_environment>`
to configure other publishing targets.
</note>

### Referencing The Pipeline

A project will be recognized by including in a `.yw_pipeline/yw_pipeline.py` file the definition of
a class `PipelineFactory`, such as:

<code-snippet language="python">
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.projects import IPipelineFactory, BrowserAppBundle, Execution, BrowserAppGraphics
from youwol.pipelines.pipeline_raw_app import pipeline, PipelineConfig
from youwol.utils.context import Context


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, _env: YouwolEnvironment, context: Context):

        graphics = BrowserAppGraphics(
            appIcon={ 'class': 'far fa-laugh-beam fa-2x' }
        )
        config = PipelineConfig(
            target=BrowserAppBundle(
                displayName="My application",
                execution=Execution(standalone=True),
                graphics=graphics
            )
        )
        return await pipeline(config, context)
</code-snippet>

<note level="warning" label="Important">
To use this pipeline, the project folder must contain a `package.json` file featuring at least the attributes:
*  `name`: The name of the package.
*  `version`: The version of the package.
*  `main`: The path to the `index.html` file.

</note>

You can find an example of a project organization
<a target="_blank" href="https://github.com/youwol/todo-app-js" >here</a>.

### Skeleton Generation

The pipeline offers the function
:func:`template <youwol.pipelines.pipeline_raw_app.template.template>` to automatise project creation from
the `co-lab` application.
"""

# relative
from .pipeline import *
