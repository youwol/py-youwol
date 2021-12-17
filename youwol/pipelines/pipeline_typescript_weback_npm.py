from pathlib import Path
from typing import Union, List

from configuration import Link
from youwol.configuration import Flow, SourcesFctImplicit
from youwol.context import Context
from youwol.pipelines.publish_cdn import PublishCdnLocalStep, PublishCdnRemoteStep

from youwol.configuration import (
    Pipeline, parse_json, Skeleton, SkeletonParameter, PipelineStep, FileListing,
    Artifact, Project
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


def get_dependencies(project: Project):
    package_json = parse_json(project.path / "package.json")
    return set({
        **package_json.get("dependencies", {}),
        **package_json.get("peerDependencies", {}),
        **package_json.get("devDependencies", {})
        }.keys())


class SyncFromDownstreamStep(PipelineStep):
    id: str = "sync-deps"
    run: str = ""

    artifacts: List[Artifact] = []


class BuildStep(PipelineStep):
    id: str
    run: str
    sources: FileListing = FileListing(
        include=["package.json", "webpack.config.js", "src/lib", "src/index.ts"],
        ignore=["**/auto_generated.ts"]
        )

    artifacts: List[Artifact] = [
        Artifact(
            id='dist',
            files=FileListing(
                include=["package.json", "dist"],
                ignore=["dist/docs"]
                )
            )
        ]


class DocStep(PipelineStep):
    id = 'doc'
    run: str = "yarn doc"
    sources: FileListing = FileListing(
        include=["src/lib", "src/index.ts"],
        ignore=["**/auto_generated.ts"]
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
        ),
    links=[
        Link(
            name='Coverage',
            url='coverage/lcov-report/index.html'
            )
        ]
    )


class TestStep(PipelineStep):
    id: str
    run: str
    artifacts: List[Artifact]

    @staticmethod
    async def _sources(project: Project, flow_id: str, _context: Context):
        steps_in_flow = project.get_flow_steps(flow_id=flow_id)
        build_step = next(s for s in steps_in_flow if isinstance(s, BuildStep))

        return FileListing(
            include=build_step.sources.include + ["src/tests"]
            )

    sources: SourcesFctImplicit = lambda p, f, ctx: TestStep._sources(p, f, ctx)


def pipeline():
    return Pipeline(
        id="typescript-webpack-npm",
        language="typescript",
        compiler="webpack",
        output="javascript",
        projectName=lambda path: parse_json(path / "package.json")["name"],
        projectVersion=lambda path: parse_json(path / "package.json")["version"],
        dependencies=lambda project, ctx: get_dependencies(project),
        skeleton=lambda ctx: create_skeleton(ctx),
        steps=[
            SyncFromDownstreamStep(),
            BuildStep(id="build-dev", run="yarn build:dev"),
            BuildStep(id="build-prod", run="yarn build:prod"),
            DocStep(),
            TestStep(id="test", run="yarn test", artifacts=[test_result]),
            TestStep(id="test-coverage", run="yarn test-coverage",
                     artifacts=[test_coverage]
                     ),
            PublishCdnLocalStep(packagedArtifacts=['dist', 'docs']),
            PublishCdnRemoteStep(packagedArtifacts=['dist', 'docs'])
            ],
        flows=[
            Flow(
                name="prod",
                dag=[
                    "sync-deps > build-prod > test > publish-local > publish-remote ",
                    "build-prod > doc > publish-local",
                    "build-prod > test-coverage"
                    ]
                ),
            Flow(
                name="dev",
                dag=[
                    "sync-deps > build-dev > publish-local",
                    "build-dev > doc > publish-local"
                    ]
                )
            ]
        )
