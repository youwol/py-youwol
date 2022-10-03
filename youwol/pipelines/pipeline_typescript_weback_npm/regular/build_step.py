from typing import List

from youwol.environment.models_project import PipelineStep, FileListing, Artifact, Link
from youwol.pipelines.pipeline_typescript_weback_npm.regular.common import Paths


class BuildStep(PipelineStep):
    id: str
    run: str
    sources: FileListing = FileListing(
        include=[Paths.package_json_file, "webpack.config.js", 'template.py', Paths.lib_folder, "src/app",
                 "src/index.ts", "src/tests", "yarn.lock"],
        ignore=[Paths.auto_generated_file, "**/.*/*", '.template/**', "node_modules", "**/node_modules"]
    )

    artifacts: List[Artifact] = [
        Artifact(
            id='dist',
            files=FileListing(
                include=[Paths.package_json_file, "dist", "src"],
                ignore=["dist/docs", '.template/**', "**/node_modules"]
            ),
            links=[
                Link(
                    name='bundle-analysis',
                    url='dist/bundle-analysis.html'
                )
            ]
        )
    ]

