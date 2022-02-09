from pathlib import Path
from typing import List, Optional, Set, Callable

import pkg_resources
from pydantic import BaseModel

from youwol.environment.models import K8sInstance
from youwol.environment.models_project import Manifest, PipelineStepStatus, Link, Flow, \
    SourcesFctImplicit, Pipeline, PipelineStep, FileListing, \
    Artifact, Project, RunImplicit, MicroService
from youwol.pipelines.docker_k8s_helm import get_helm_version, InstallHelmStep, InstallHelmStepConfig, \
    PublishDockerStepConfig, PublishDockerStep
from youwol.pipelines.publish_cdn import PublishCdnRemoteStep, PublishCdnLocalStep
from youwol_utils.context import Context


def get_dependencies(project: Project) -> Set[str]:
    with (project.path / 'requirements.txt').open() as requirements_txt:
        install_requires = [
            str(requirement)
            for requirement
            in pkg_resources.parse_requirements(requirements_txt)
        ]
    return set(install_requires)


class PreconditionChecksStep(PipelineStep):
    id: str = 'checks'
    run: str = ''

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:
        return PipelineStepStatus.OK


class InitStep(PipelineStep):
    id: str = 'init'
    run: str = 'python3.9 -m venv ./src/.virtualenv '\
               '&& . ./src/.virtualenv/bin/activate ' \
               '&& pip install -r requirements.txt'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:
        if (project.path / 'src' / '.virtualenv').exists():
            return PipelineStepStatus.OK
        return PipelineStepStatus.none


def to_module_name(dir_name: str):
    return dir_name.replace('-', '_')


class DocStepConfig(BaseModel):
    venvPath: Path = Path('.') / 'src' / '.virtualenv'
    srcPath: Path = Path('.') / 'src'
    outputDir: Path = Path('.') / 'dist' / 'docs'

    def cmd(self, project: Project) -> str:
        return f"""
. {self.venvPath}/bin/activate && 
pdoc {self.srcPath} --html --force --output-dir {self.outputDir} &&
mv {self.outputDir}/{to_module_name(project.name)}/* {self.outputDir}
"""


class DocStep(PipelineStep):
    config: DocStepConfig
    id = 'doc'

    run: RunImplicit = \
        lambda self, project, flow_id, ctx: self.conf.cmd(project)

    sources: SourcesFctImplicit = \
        lambda self, project, flow_id, step_id: \
            FileListing(include=[f"src/{project.name.replace('-', '_')}"])

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


class UnitTestStep(PipelineStep):

    id: str = "unit-test"

    run: RunImplicit = \
        lambda self, project, flow_id, ctx: \
        f". ./src/.virtualenv/bin/activate && " \
        f"pytest --cov=src/{to_module_name(project.name)} " \
        "--cov-report=html:dist/tests/html_dir"

    artifacts: List[Artifact] = [
        Artifact(
            id='test-coverage',
            files=FileListing(
                include=["dist/tests/html_dir"],
            ),
            links=[
                Link(
                    name='Coverage',
                    url='dist/tests/html_dir/index.html'
                )
            ]
        )
    ]

    sources: SourcesFctImplicit = lambda self, project, flow_id, step_id: FileListing(
        include=[f"src/{to_module_name(project.name)}", 'src/tests']
        )


class IntegrationTestStep(PipelineStep):
    id: str = "integration-test"
    run: str = "ls"


class ApiTestStep(PipelineStep):
    id: str = "api-test"
    run: str = "ls"


class ConfPublishDocker(BaseModel):
    registry_path: Callable[[Project, Context], str]


class ConfDeploy(BaseModel):
    host: str
    open_id_host: str
    secret_youwol_auth: Path
    secret_gitlab_docker: Path


def get_ingress(host: str):
    return {
        "hosts[0].host": host
        }


class PipelineConfig(BaseModel):
    tags: List[str] = []
    k8sInstance: K8sInstance
    docConfig: DocStepConfig
    dockerConfig: PublishDockerStepConfig
    helmConfig: InstallHelmStepConfig


def pipeline(
        config: PipelineConfig,
        context: Context
):
    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline", data=config)

        return Pipeline(
            target=MicroService(),
            tags=['python', 'microservice', 'fastapi'],
            projectName=lambda path: Path(path).name,
            projectVersion=lambda path: get_helm_version(path),
            dependencies=lambda project, _ctx: get_dependencies(project),
            steps=[
                PreconditionChecksStep(),
                InitStep(),
                DocStep(config=config.docConfig),
                UnitTestStep(),
                ApiTestStep(),
                IntegrationTestStep(),
                PublishCdnLocalStep(packagedArtifacts=['docs', 'test-coverage']),
                PublishCdnRemoteStep(),
                PublishDockerStep(
                    config=config.dockerConfig
                ),
                InstallHelmStep(
                    config=config.helmConfig
                )
            ],
            flows=[
                Flow(
                    name="prod",
                    dag=[
                        "checks > init > unit-test > integration-test > publish-docker > install-helm > api-test ",
                        "init > doc ",
                        "unit-test > publish-local > publish-remote"
                    ]
                )
            ]
        )
