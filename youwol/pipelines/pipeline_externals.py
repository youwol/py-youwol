from pathlib import Path
from typing import List, Any, Union

from pydantic import BaseModel

from youwol.environment.models_project import Flow, \
    Pipeline, parse_json, External, PipelineStep, Artifact, FileListing
from youwol.pipelines.publish_cdn import PublishCdnLocalStep, PublishCdnRemoteStep
from youwol_utils.context import Context


class PipelineConfig(BaseModel):
    external_artifacts: List[Union[Path, str]]


class ListArtifacts(PipelineStep):
    id: str = "list-artifacts"

    run: str = "echo listing artifacts"

    def __init__(self, external_artifacts: List[str], **data: Any):
        super().__init__(**data)
        listing = FileListing(include=external_artifacts + ["package.json"])
        self.artifacts = [Artifact(
            id="external",
            files=listing
        )]
        self.sources = listing


async def pipeline(config: PipelineConfig, context: Context):
    artifacts = [str(path) for path in config.external_artifacts]
    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline")
        return Pipeline(
            target=External(),
            tags=["external"],
            projectName=lambda path: parse_json(path / "package.json")["name"],
            projectVersion=lambda path: parse_json(path / "package.json")["version"],
            dependencies=lambda path, _ctx: set(),
            steps=[
                ListArtifacts(external_artifacts=artifacts),
                PublishCdnLocalStep(packagedArtifacts=["external"]),
                PublishCdnRemoteStep()
            ],
            flows=[
                Flow(
                    name="prod",
                    dag=["list-artifacts > publish-local > publish-remote"]
                )
            ]
        )
