# standard library
from pathlib import Path

# typing
from typing import List, Optional

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.routers.projects.models_project import (
    Artifact,
    FileListing,
    Flow,
    JsBundle,
    Link,
    Pipeline,
    PipelineStep,
)

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.utils_paths import parse_json

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm import (
    DependenciesStep,
    PublishConfig,
    SetupStep,
    TestStep,
    create_sub_pipelines_publish_cdn,
    get_environment,
)
from youwol.pipelines.publish_cdn import PublishCdnLocalStep


class BuildStep(PipelineStep):
    id: str = "build"
    run: str = "yarn build:prod"
    sources: FileListing = FileListing(
        include=["*", "**"],
        ignore=[".yw_pipeline/**", "cdn.zip", "node_modules/**", ".template/**"],
    )

    artifacts: List[Artifact] = [
        Artifact(
            id="dist",
            files=FileListing(
                include=["*", "**"],
                ignore=[".yw_pipeline/**", "cdn.zip", "node_modules", ".template/**"],
            ),
            links=[Link(name="bundle-analysis", url="./dist/bundle-analysis.html")],
        )
    ]


class PipelineConfig(BaseModel):
    target: JsBundle = JsBundle(
        links=[Link(name="bundle-analysis", url="dist/bundle-analysis.html")]
    )
    customInitStep: Optional[PipelineStep] = None
    customBuildStep: Optional[PipelineStep] = None
    publishConfig: PublishConfig = PublishConfig(packagedArtifacts=["dist"])


async def pipeline(config: PipelineConfig, context: Context) -> Pipeline:
    def get_name(path: Path):
        package_json = parse_json(path / "package.json")
        return f'{package_json["name"]}~{package_json["version"]}'

    init_step = config.customInitStep or SetupStep()
    build_step = config.customBuildStep or BuildStep()
    dependencies_step = DependenciesStep()
    cdn_local_step = PublishCdnLocalStep(
        packagedArtifacts=config.publishConfig.packagedArtifacts,
        packagedFolders=config.publishConfig.packagedFolders,
    )
    test_step = TestStep(id="test", run="yarn test", artifacts=[])
    publish_remote_steps, dags = await create_sub_pipelines_publish_cdn(
        start_step=test_step.id, context=context, targets=get_environment().cdnTargets
    )
    return Pipeline(
        target=config.target,
        tags=["typescript", "webpack", "library", "npm", "external"],
        projectName=get_name,
        projectVersion=lambda path: parse_json(path / "package.json")["version"],
        steps=[
            init_step,
            dependencies_step,
            build_step,
            test_step,
            PublishCdnLocalStep(packagedArtifacts=["dist"]),
            *publish_remote_steps,
        ],
        flows=[
            Flow(
                name="prod",
                dag=[
                    f"{init_step.id} > {dependencies_step.id} > {build_step.id} > {cdn_local_step.id} > {test_step.id}",
                    *dags,
                ],
            )
        ],
    )
