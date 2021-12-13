from pathlib import Path
from typing import Any, Union, List

from context import Context
from youwol.configuration import (
    Pipeline, parse_json, Skeleton, SkeletonParameter, PipelineStep, FileListing,
    Artifact, Runnable, Project, PipelineStepStatus
    )


def create_skeleton(path: Union[Path, str]):
    async def generate():
        return

    return Skeleton(
        folder=path,
        description="A skeleton of npm package written in typescript and build with webpack.",
        parameters=[
            SkeletonParameter(
                id="package-name",
                displayName="Name",
                type='string',
                defaultValue=None,
                placeholder="Package name",
                description="Name of the package. Should follow npm semantic.",
                required=True
                )
            ],
        generate=generate
        )


def get_dependencies(project: Any):
    package_json = parse_json(project.path / "package.json")
    return package_json.get("dependencies", {}).keys() + \
        package_json.get("peerDependencies", []).keys() + \
        package_json.get("devDependencies", []).keys()


class BuildStep(PipelineStep):
    id: str
    run: Runnable
    sources: FileListing = FileListing(
        include=["package.json", "webpack.config.js", "src/lib", "src/index.ts"],
        ignore=["**/auto_generated.ts"]
        )

    artifacts: List[Artifact] = [
        Artifact(
            id='dist',
            files=FileListing(
                include=["package.json", "dist/lib", "dist/@youwol"],
                )
            )
        ]


class DocStep(PipelineStep):
    id = 'doc'
    run: Runnable = "yarn doc"
    sources = FileListing(
        include=["src/lib", "src/index.ts"],
        ignore=["**/auto_generated.ts"]
        )

    artifacts: List[Artifact] = [
        Artifact(
            id='docs',
            files=FileListing(
                include=["dist/docs"],
                )
            )
        ]


test_result: Artifact = Artifact(
        id='test-result',
        files=FileListing(
            include=["junit.xml"],
            )
        )
test_coverage: Artifact = Artifact(
    id='test-coverage',
    files=FileListing(
        include=["coverage"],
        )
    )


class TestStep(PipelineStep):
    id: str
    run: str
    artifacts: List[Artifact]
    sources = FileListing(
        include=["src/tests", "src/index.ts"]
        )


def cdn_local_status(_project, _context):
    """
    compare check sum of sources with LocalClients.cdn_client.check_sum(project.name, project.version)
    """
    return PipelineStepStatus.KO


class PublishCdnLocalStep(PipelineStep):
    id = 'publish-local'

    # @staticmethod
    # def sources(project: Project, context: Context):
    #     return [
    #         project.path / 'package.json',
    #         project.path / 'webpack.config.js'
    #         ] + \
    #         project.get_artifact('dist') + \
    #         project.get_artifact('doc')

    def run(self, project: Project, context: Context):
        """
        open a tmp.zip and add PublishCdnLocalStep.sources(project, context)

        send the tmp.zip using LocalClients.cdn_backend()
        """
        pass


def cdn_remote_status(_project: Project, _context: Context):
    """
    switch:
        + the (_project.name, _project.version) not in remote CDN => PipelineStepStatus.none
        + the (_project.name, _project.version) in remote CDN and fingerprint match local CDN fingerprint =>
            PipelineStatus.OK
        + otherwise => PipelineStatus.KO
    """
    return PipelineStepStatus.KO


class PublishCdnRemoteStep(PipelineStep):
    id = 'publish-remote'

    def run(self, project: Project, context: Context):
        pass


def pipeline():
    return Pipeline(
        id="typescript-webpack-npm",
        language="typescript",
        compiler="webpack",
        output="javascript",
        projectName=lambda path: parse_json(path / "package.json")["name"],
        projectVersion=lambda path: parse_json(path / "package.json")["version"],
        dependencies=lambda project: get_dependencies(project),
        skeleton=lambda ctx: create_skeleton(ctx),
        steps=[
            BuildStep(id="build-dev", run="yarn build:dev"),
            BuildStep(id="build-prod", run="yarn build:prod"),
            DocStep(),
            TestStep(id="test", run="yarn test", artifacts=[test_result]),
            TestStep(id="test-coverage", run="yarn test-coverage",
                     artifacts=[test_result, test_coverage]
                     ),
            PublishCdnLocalStep(),
            PublishCdnRemoteStep()
            ],
        flow=[
            "build-dev > test > publish-local > publish-remote ",
            "build-prod > test",
            "build-dev > doc > publish-remote",
            "build-prod > doc",
            "build-dev > test-coverage"
            ]
        )
