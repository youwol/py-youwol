import shutil
from pathlib import Path
from typing import List, Optional, Set, Callable

import pkg_resources
from pydantic import BaseModel

import youwol_utils
from youwol.environment.models import K8sInstance
from youwol.environment.models_project import Manifest, PipelineStepStatus, Link, Flow, \
    SourcesFctImplicit, Pipeline, PipelineStep, FileListing, \
    Artifact, Project, RunImplicit, MicroService, ExplicitNone
from youwol.exceptions import CommandException
from youwol.pipelines.docker_k8s_helm import get_helm_version, InstallHelmStep, InstallHelmStepConfig, \
    PublishDockerStep, PublishDockerStepConfig
from youwol.pipelines.publish_cdn import PublishCdnRemoteStep, PublishCdnLocalStep
from youwol.utils.utils_low_level import execute_shell_cmd
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


class CustomPublishDockerStep(PublishDockerStep):
    sources: FileListing = FileListing(
        include=[f"src", 'Dockerfile'],
        ignore=["src/.virtualenv"]
    )

    run: ExplicitNone = ExplicitNone()

    async def execute_run(self, project: Project, flow_id: str, context: Context):
        src_path = Path(youwol_utils.__file__).parent
        dest_path = project.path / 'src' / 'youwol_utils'
        outputs = []

        async def cp_youwol_utils(ctx_enter: Context):
            shutil.rmtree(dest_path, ignore_errors=True)
            shutil.copytree(src_path, dest_path)
            outputs.append(f"cp {src_path} {dest_path}")
            await ctx_enter.info(text="successfully copied youwol_utils")

        async def rm_youwol_utils(ctx_exit: Context):
            outputs.append(f"rm {dest_path}")
            await ctx_exit.info(text="successfully removed youwol_utils")
            shutil.rmtree(dest_path, ignore_errors=True)

        async with context.start(
                action="Publish docker image with youwol_utils copy",
                on_enter=cp_youwol_utils,
                on_exit=rm_youwol_utils
        ) as ctx:  # type: Context
            cmd = self.docker_build_command(project, context)
            return_code, cmd_outputs = await execute_shell_cmd(cmd=f"( cd {project.path} && {cmd})", context=ctx)
            outputs = outputs + cmd_outputs
            if return_code > 0:
                raise CommandException(command=cmd, outputs=outputs)
            return outputs


async def pipeline(
        config: PipelineConfig,
        context: Context
):
    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline", data=config)

        docker_fields = {k: v for k, v in config.dockerConfig.dict().items() if v is not None}

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
                CustomPublishDockerStep(**docker_fields),
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
