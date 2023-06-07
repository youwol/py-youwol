# typing
from typing import List

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.routers.projects.models_project import (
    BrowserLibBundle,
    BrowserTarget,
    Flow,
    Pipeline,
    parse_json,
)

# Youwol utilities
from youwol.utils.context import Context

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm import create_sub_pipelines_publish
from youwol.pipelines.pipeline_typescript_weback_npm.regular.build_step import BuildStep
from youwol.pipelines.pipeline_typescript_weback_npm.regular.common import (
    Paths,
    get_dependencies,
)
from youwol.pipelines.pipeline_typescript_weback_npm.regular.dependencies_step import (
    DependenciesStep,
)
from youwol.pipelines.pipeline_typescript_weback_npm.regular.doc_step import DocStep
from youwol.pipelines.pipeline_typescript_weback_npm.regular.setup_step import SetupStep
from youwol.pipelines.pipeline_typescript_weback_npm.regular.test_step import (
    TestStep,
    TestStepConfig,
)
from youwol.pipelines.publish_cdn import PublishCdnLocalStep


class PublishConfig(BaseModel):
    packagedArtifacts: List[str] = ["dist", "docs", "test-coverage"]
    packagedFolders: List[str] = []


class PipelineConfig(BaseModel):
    target: BrowserTarget = BrowserLibBundle()
    with_tags: List[str] = []
    testConfig: TestStepConfig = TestStepConfig()
    publishConfig: PublishConfig = PublishConfig()


async def pipeline(config: PipelineConfig, context: Context):
    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline", data=config)

        publish_remote_steps, dags = await create_sub_pipelines_publish(
            start_step="cdn-local", context=ctx
        )

        return Pipeline(
            target=config.target,
            tags=["typescript", "webpack", "npm"] + config.with_tags,
            projectName=lambda path: parse_json(path / Paths.package_json_file)["name"],
            projectVersion=lambda path: parse_json(path / Paths.package_json_file)[
                "version"
            ],
            dependencies=lambda project, _ctx: get_dependencies(project),
            steps=[
                SetupStep(),
                DependenciesStep(),
                BuildStep(id="build-dev", run="yarn build:dev"),
                BuildStep(id="build-prod", run="yarn build:prod"),
                DocStep(),
                TestStep(
                    id="test",
                    run="yarn test-coverage",
                    artifacts=config.testConfig.artifacts,
                ),
                PublishCdnLocalStep(
                    packagedArtifacts=config.publishConfig.packagedArtifacts,
                    packagedFolders=config.publishConfig.packagedFolders,
                ),
                *publish_remote_steps,
            ],
            flows=[
                Flow(
                    name="prod",
                    dag=[
                        "setup > dependencies > build-prod > test > cdn-local",
                        "build-prod > doc > cdn-local",
                        *dags,
                    ],
                )
            ],
        )
