from typing import List

from youwol.pipelines.pipeline_typescript_weback_npm.regular.common import Paths
from youwol.routers.projects.models_project import PipelineStep, FileListing, Artifact, Link


class DocStep(PipelineStep):
    id = 'doc'
    run: str = "yarn doc"
    sources: FileListing = FileListing(
        include=["src", "typedoc.js"],
        ignore=[Paths.auto_generated_file, "**/.*/*", "src/tests"]
    )

    artifacts: List[Artifact] = [
        Artifact(
            id='docs',
            files=FileListing(
                include=["dist/docs"],
            ),
            links=[
                Link(
                    name='documentation',
                    url='dist/docs/index.html'
                )
            ]
        )
    ]
