from pathlib import Path
from typing import List

from pydantic import BaseModel
from youwol.environment.models_project import Artifact, Flow, Pipeline, PipelineStep, FileListing, JsBundle, Link
from youwol.pipelines.pipeline_typescript_weback_npm.common import InitStep
from youwol.pipelines.publish_cdn import PublishCdnRemoteStep, PublishCdnLocalStep
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json


class BuildStep(PipelineStep):
    id: str = "build"
    run: str = "yarn build:prod"
    sources: FileListing = FileListing(
        include=["*", "**"],
        ignore=['.yw_pipeline/**', 'cdn.zip', 'node_modules/**', '.template/**']
    )

    artifacts: List[Artifact] = [
        Artifact(
            id='dist',
            files=FileListing(
                include=["*", "**"],
                ignore=['.yw_pipeline/**', 'cdn.zip', 'node_modules', '.template/**']
            ),
            links=[
                Link(
                    name='bundle-analysis',
                    url='./dist/bundle-analysis.html'
                )
            ]
        )
    ]


class PipelineConfig(BaseModel):
    target: JsBundle = JsBundle(links=[Link(name="bundle-analysis", url="dist/bundle-analysis.html")])


async def pipeline(config: PipelineConfig, context: Context) -> Pipeline:
    def get_name(path: Path):
        package_json = parse_json(path / "package.json")
        return f'{package_json["name"]}~{package_json["version"]}'

    return Pipeline(
        target=config.target,
        tags=["typescript", "webpack", "library", "npm", "external"],
        projectName=get_name,
        projectVersion=lambda path: parse_json(path / "package.json")["version"],
        steps=[
            InitStep(),
            BuildStep(),
            PublishCdnLocalStep(packagedArtifacts=['dist']),
            PublishCdnRemoteStep()
        ],
        flows=[
            Flow(
                name="prod",
                dag=[
                    "init > build > publish-local > publish-remote "
                ]
            )
        ]
    )