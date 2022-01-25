import functools
import shutil
from pathlib import Path
from typing import Union, List, Optional, NamedTuple, Iterable, Mapping

from youwol.environment.models_project import Manifest, PipelineStepStatus, Link, ExplicitNone, Flow, \
    Pipeline, parse_json, Skeleton, SkeletonParameter, PipelineStep, FileListing, \
    Artifact, Project, FlowId
from youwol.environment.paths import PathsBook
from youwol.environment.projects_loader import ProjectLoader
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.pipelines.publish_cdn import PublishCdnLocalStep, PublishCdnRemoteStep
from youwol_utils import files_check_sum
from youwol_utils import to_json
from youwol_utils.context import Context
from youwol_utils.utils_paths import copy_tree, copy_file, list_files


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


class InputDataDependency(NamedTuple):
    project: Project
    dist_folder: Path
    src_folder: Path
    dist_files: Iterable[Path]
    src_files: Iterable[Path]
    checksum: str


class SyncFromDownstreamStep(PipelineStep):
    id: str = "sync-deps"
    run: ExplicitNone = ""

    artifacts: List[Artifact] = []

    @staticmethod
    async def get_input_data(project: Project, flow_id: str, context: Context) -> Mapping[str, InputDataDependency]:

        env = await context.get('env', YouwolEnvironment)
        paths_book: PathsBook = env.pathsBook

        project_step = [(d, next((s for s in d.get_flow_steps(flow_id=flow_id) if isinstance(s, BuildStep)), None))
                        for d in await project.get_dependencies(recursive=True,
                                                                projects=await ProjectLoader.get_projects(env, context),
                                                                context=context
                                                                )
                        ]

        def is_succeeded(p: Project, s: BuildStep):
            manifest = p.get_manifest(flow_id=flow_id, step=s, env=env)
            return manifest.succeeded if manifest else False

        dependencies = [(project, step) for project, step in project_step
                        if step is not None and is_succeeded(project, step)]

        dist_folders = {project.name: paths_book.artifact(project.name, flow_id, step.id, step.artifacts[0].id)
                        for project, step in dependencies}
        dist_files = {name: list_files(folder) for name, folder in dist_folders.items()}
        src_files = {p.name: list_files(p.path / 'src') for p, s in dependencies}
        return {project.name: InputDataDependency(
            project=project,
            dist_folder=dist_folders[project.name],
            src_folder=project.path / 'src',
            dist_files=dist_files[project.name],
            src_files=src_files[project.name],
            checksum=files_check_sum(dist_files[project.name] + src_files[project.name]))
            for project, step in dependencies}

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        async with context.start(action="get status of project's dependencies") as ctx:
            if last_manifest is None:
                return PipelineStepStatus.none
            if not last_manifest.succeeded:
                return PipelineStepStatus.KO

            await ctx.info(text='previous manifest', data=to_json(last_manifest))
            data = await SyncFromDownstreamStep.get_input_data(project=project, flow_id=flow_id, context=context)
            prev_checksums = last_manifest.cmdOutputs['checksums']
            ok = len(data.keys()) == len(prev_checksums.keys())\
                and all(k in prev_checksums and prev_checksums[k] == v.checksum for k, v in data.items())

            if not ok:
                return PipelineStepStatus.outdated

            # Any of the inner dependencies code in node_modules should be checked to make sure
            # no 'external' tool (e.g doing 'yarn') changed the node_module files
            prev_node_module_checksums = last_manifest.cmdOutputs.get('nodeModuleChecksums', {})
            node_module_checksums: Mapping[str, str] = {
                name: SyncFromDownstreamStep.node_module_checksum(project=project, name=name)
                for name in data.keys()
                }
            if not all(node_module_checksums[name] == prev_node_module_checksums.get(name, "") for name in data.keys()):
                return PipelineStepStatus.outdated

            return PipelineStepStatus.OK

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):

        async with context.start(action="run synchronization of workspace dependencies") as ctx:

            data = await SyncFromDownstreamStep.get_input_data(project=project, flow_id=flow_id, context=ctx)

            destination_folders: Mapping[str, Path] = {
                name: project.path / 'node_modules' / name for name in data.keys()
                }
            for name, p in data.items():
                if destination_folders[name].exists():
                    shutil.rmtree(destination_folders[name])
                copy_tree(p.dist_folder, destination_folders[name])
                for file in p.src_files:
                    destination = destination_folders[name] / 'src' / file.relative_to(p.src_folder)
                    copy_file(source=file, destination=destination, create_folders=True)

            all_files = functools.reduce(lambda acc, e: acc + e.src_files + e.dist_files, data.values(), [])

            return {
                'fingerprint': files_check_sum(all_files),
                'checksums': {name: d.checksum for name, d in data.items()},
                'nodeModuleChecksums': {
                    name: SyncFromDownstreamStep.node_module_checksum(project=project, name=name)
                    for name in data.keys()
                    }
                }

    @staticmethod
    def node_module_checksum(project: Project, name: str) -> Optional[str]:

        node_module_folder = project.path / 'node_modules' / name
        files = list_files(node_module_folder)
        return files_check_sum(files)


class PreconditionChecksStep(PipelineStep):
    id: str = 'checks'
    run: str = ''

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:
        return PipelineStepStatus.OK


class InitStep(PipelineStep):
    id: str = 'init'
    run: str = 'yarn'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        if (project.path / 'node_modules').exists():
            return PipelineStepStatus.OK
        return PipelineStepStatus.none


class BuildStep(PipelineStep):
    id: str
    run: str
    sources: FileListing = FileListing(
        include=["package.json", "webpack.config.js", "src/lib", "src/app", "src/index.ts", "src/tests"],
        ignore=["**/auto_generated.ts", "**/.*/*"]
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

    sources: FileListing = FileListing(
        include=["package.json", "src/tests"],
        ignore=["**/auto_generated.ts", "**/.*/*"]
    )


def pipeline():
    return Pipeline(
        id=__name__,
        language="typescript",
        compiler="webpack",
        output="javascript",
        projectName=lambda path: parse_json(path / "package.json")["name"],
        projectVersion=lambda path: parse_json(path / "package.json")["version"],
        dependencies=lambda project, ctx: get_dependencies(project),
        skeleton=lambda ctx: create_skeleton(ctx),
        steps=[
            PreconditionChecksStep(),
            InitStep(),
            SyncFromDownstreamStep(),
            BuildStep(id="build-dev", run="yarn build:dev"),
            BuildStep(id="build-prod", run="yarn build:prod"),
            DocStep(),
            TestStep(id="test", run="yarn test", artifacts=[test_result]),
            TestStep(id="test-coverage", run="yarn test-coverage",
                     artifacts=[test_coverage]
                     ),
            PublishCdnLocalStep(packagedArtifacts=['dist', 'docs']),
            PublishCdnRemoteStep()
            ],
        flows=[
            Flow(
                name="prod",
                dag=[
                    "checks > init > sync-deps > build-prod > test > publish-local > publish-remote ",
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
