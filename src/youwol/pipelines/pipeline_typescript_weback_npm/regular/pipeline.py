# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.routers.projects.models_project import (
    BrowserLibBundle,
    BrowserTarget,
    Flow,
    Pipeline,
    PipelineStep,
    parse_json,
)

# Youwol utilities
from youwol.utils.context import Context

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm.common import (
    create_sub_pipelines_publish,
)
from youwol.pipelines.publish_cdn import PublishCdnLocalStep

# relative
from .build_step import BuildStep
from .common import Paths, get_dependencies
from .dependencies_step import DependenciesStep
from .doc_step import DocStep
from .setup_step import SetupStep
from .test_step import TestStep, TestStepConfig


class PublishConfig(BaseModel):
    packagedArtifacts: list[str] = ["dist", "docs", "test-coverage"]
    packagedFolders: list[str] = []


class PipelineConfig(BaseModel):
    target: BrowserTarget = BrowserLibBundle()
    with_tags: list[str] = []
    testConfig: TestStepConfig = TestStepConfig()
    publishConfig: PublishConfig = PublishConfig()
    overridenSteps: list[PipelineStep] = []


async def pipeline(config: PipelineConfig, context: Context):
    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline", data=config)

        publish_remote_steps, dags = await create_sub_pipelines_publish(
            start_step="cdn-local", context=ctx
        )

        default_steps = [
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
        ]
        overriden_steps = {step.id: step for step in config.overridenSteps}
        steps_dict = {
            step.id: overriden_steps.get(step.id, step) for step in default_steps
        }
        return Pipeline(
            target=config.target,
            tags=["typescript", "webpack", "npm"] + config.with_tags,
            projectName=lambda path: parse_json(path / Paths.package_json_file)["name"],
            projectVersion=lambda path: parse_json(path / Paths.package_json_file)[
                "version"
            ],
            dependencies=lambda project, _ctx: get_dependencies(project),
            steps=list(steps_dict.values()),
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
