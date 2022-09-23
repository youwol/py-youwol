import shutil
from pathlib import Path
from typing import List, Optional, Set, Callable

import pkg_resources
import yaml
from pydantic import BaseModel

import youwol_utils
from youwol.configuration.models_k8s import HelmChartsInstall
from youwol.environment.models import K8sInstance
from youwol.environment.models_project import Manifest, PipelineStepStatus, Link, Flow, \
    SourcesFctImplicit, Pipeline, PipelineStep, FileListing, \
    Artifact, Project, RunImplicit, MicroService, ExplicitNone
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.exceptions import CommandException
from youwol.pipelines.docker_k8s_helm import get_helm_app_version, InstallHelmStep, InstallHelmStepConfig, \
    PublishDockerStep, PublishDockerStepConfig, InstallDryRunHelmStep
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


class PullStep(PipelineStep):
    id: str = 'pull'
    run: str = 'git pull'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd {project.path} && git log HEAD..origin/master --oneline)",
            context=context)
        if return_code != 0:
            return PipelineStepStatus.KO
        return PipelineStepStatus.OK if not outputs else PipelineStepStatus.outdated


class NewBranchStep(PipelineStep):
    id: str = 'new-branch'
    run: RunImplicit = \
        lambda self, project, flow_id, ctx: f'git checkout -b feature/{project.version}'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd {project.path} && git branch --show-current)",
            context=context)
        if return_code != 0 or len(outputs) != 1:
            await context.info("Error while retrieving current branch name")
            return PipelineStepStatus.KO

        return PipelineStepStatus.OK if f'feature/{project.version}' in outputs[0] else PipelineStepStatus.outdated


class UpdatePyYouwolStep(PipelineStep):

    id: str = 'sync-pyYw'
    run: str = 'git submodule update --init ./py-youwol && git submodule update --remote ./py-youwol'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd {project.path}/py-youwol && git log HEAD..origin/master --oneline)",
            context=context)
        if return_code != 0:
            return PipelineStepStatus.KO
        return PipelineStepStatus.OK if not outputs else PipelineStepStatus.outdated


class SyncHelmDeps(PipelineStep):

    id: str = 'sync-helm-deps'
    run: str = 'helm dependency update ./chart'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        with open(project.path / 'chart' / 'Chart.yaml') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            expected_charts = [f"{d['name']}-{d['version']}.tgz" for d in data['dependencies']]
            all_here = all([(project.path / 'chart' / 'charts' / c).exists() for c in expected_charts])
            return PipelineStepStatus.OK if all_here else PipelineStepStatus.outdated


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


class CustomPublishDockerStepConfig(PublishDockerStepConfig):
    python_modules_copied: List[Path] = []


class PipelineConfig(BaseModel):
    tags: List[str] = []
    k8sInstance: K8sInstance
    docConfig: DocStepConfig
    dockerConfig: CustomPublishDockerStepConfig
    helmConfig: InstallHelmStepConfig


class CustomPublishDockerStep(PublishDockerStep):

    python_modules_copied: List[Path] = [Path(youwol_utils.__file__)]
    sources: FileListing = FileListing(
        include=[f"src", 'Dockerfile'],
        ignore=["src/.virtualenv"]
    )

    run: ExplicitNone = ExplicitNone()

    async def execute_run(self, project: Project, flow_id: str, context: Context):
        outputs = []

        async def cp_youwol_utils(ctx_enter: Context):
            for module_path in self.python_modules_copied:
                src_path = module_path
                dest_path = project.path / 'src' / module_path.name
                shutil.rmtree(dest_path, ignore_errors=True)
                shutil.copytree(src_path, dest_path)
                outputs.append(f"cp {src_path} {dest_path}")
                await ctx_enter.info(text="successfully copied youwol_utils")

        async def rm_youwol_utils(ctx_exit: Context):
            for module_path in self.python_modules_copied:
                dest_path = project.path / 'src' / module_path.name
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
    def add_dry_values(p, c):
        base = config.helmConfig.overridingHelmValues(p, c) if config.helmConfig.overridingHelmValues else {}
        return {
            **base,
            "platformDomain": "platform.dev.example.com",
            "clusterVersion": "v1"
        }

    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline", data=config)

        docker_fields = {k: v for k, v in config.dockerConfig.dict().items() if v is not None}
        env: YouwolEnvironment = await ctx.get('env', YouwolEnvironment)
        dry_run_config = InstallHelmStepConfig(**config.helmConfig.dict())
        dry_run_config.overridingHelmValues = add_dry_values
        k8s = next(deployment for deployment in env.pipelinesSourceInfo.uploadTargets
                   if isinstance(deployment, HelmChartsInstall))

        install_helm_steps = [InstallHelmStep(id=f'install-helm_{k8sTarget.name}',
                                              config=config.helmConfig,
                                              k8sContext=k8sTarget.context)
                              for k8sTarget in k8s.targets]

        dags = [f'dry-run-helm > install-helm_{k8sTarget.name}' for k8sTarget in k8s.targets]

        return Pipeline(
            target=MicroService(),
            tags=['python', 'microservice', 'fastapi'],
            projectName=lambda path: Path(path).name,
            projectVersion=lambda path: get_helm_app_version(path),
            dependencies=lambda project, _ctx: get_dependencies(project),
            steps=[
                PreconditionChecksStep(),
                PullStep(),
                NewBranchStep(),
                UpdatePyYouwolStep(),
                CustomPublishDockerStep(**docker_fields),
                SyncHelmDeps(),
                InstallDryRunHelmStep(
                    config=dry_run_config
                ),
                *install_helm_steps
            ],
            flows=[
                Flow(
                    name="prod",
                    dag=[
                        "checks > pull > new-branch > dry-run-helm",
                        "pull > sync-pyYw > publish-docker > dry-run-helm",
                        "pull > sync-helm-deps > dry-run-helm",
                        *dags
                    ]
                )
            ]
        )
