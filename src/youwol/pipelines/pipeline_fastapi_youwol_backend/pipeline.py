# standard library
from pathlib import Path

# typing
from typing import Callable, List, Optional, Set

# third parties
import pkg_resources
import yaml

from pydantic import BaseModel

# Youwol application
from youwol.app.routers.projects.models_project import (
    Artifact,
    FileListing,
    Flow,
    Link,
    Manifest,
    MicroService,
    Pipeline,
    PipelineStep,
    PipelineStepStatus,
    Project,
    RunImplicit,
    SourcesFctImplicit,
)

# Youwol utilities
from youwol.utils import execute_shell_cmd
from youwol.utils.context import Context

# Youwol pipelines
from youwol.pipelines.docker_k8s_helm import (
    InstallDryRunHelmStep,
    InstallHelmStep,
    InstallHelmStepConfig,
    PublishDockerStep,
    PublishDockerStepConfig,
    get_helm_app_version,
)
from youwol.pipelines.pipeline_fastapi_youwol_backend.environment import get_environment


def get_dependencies(project: Project) -> Set[str]:
    if not (project.path / "requirements.txt").exists():
        return set()
    with (project.path / "requirements.txt").open() as requirements_txt:
        install_requires = [
            str(requirement)
            for requirement in pkg_resources.parse_requirements(requirements_txt)
        ]
    return set(install_requires)


class PreconditionChecksStep(PipelineStep):
    id: str = "checks"
    run: str = ""

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        return PipelineStepStatus.OK


class PullStep(PipelineStep):
    id: str = "pull"
    run: str = "git pull"

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd {project.path} && git log HEAD..origin/master --oneline)",
            context=context,
        )
        if return_code != 0:
            return PipelineStepStatus.KO
        return PipelineStepStatus.OK if not outputs else PipelineStepStatus.outdated


class NewBranchStep(PipelineStep):
    id: str = "new-branch"
    run: RunImplicit = (
        lambda self, project, flow_id, ctx: f"git checkout -b feature/{project.version}"
    )

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd {project.path} && git branch --show-current)", context=context
        )
        if return_code != 0 or len(outputs) != 1:
            await context.info("Error while retrieving current branch name")
            return PipelineStepStatus.KO

        return (
            PipelineStepStatus.OK
            if f"feature/{project.version}" in outputs[0]
            else PipelineStepStatus.outdated
        )


class UpdatePyYouwolStep(PipelineStep):
    id: str = "sync-pyYw"
    run: str = "git submodule update --init ./py-youwol && git submodule update --remote ./py-youwol"

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd {project.path}/py-youwol && git log HEAD..origin/main --oneline)",
            context=context,
        )
        if return_code != 0:
            return PipelineStepStatus.KO
        return PipelineStepStatus.OK if not outputs else PipelineStepStatus.outdated


class SyncHelmDeps(PipelineStep):
    id: str = "sync-helm-deps"
    run: str = "helm dependency update ./chart"

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        with open(project.path / "chart" / "Chart.yaml", encoding="UTF-8") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            expected_charts = [
                f"{d['name']}-{d['version']}.tgz" for d in data["dependencies"]
            ]
            all_here = all(
                (project.path / "chart" / "charts" / c).exists()
                for c in expected_charts
            )
            return PipelineStepStatus.OK if all_here else PipelineStepStatus.outdated


def to_module_name(dir_name: str):
    return dir_name.replace("-", "_")


class DocStepConfig(BaseModel):
    venvPath: Path = Path(".") / "src" / ".virtualenv"
    srcPath: Path = Path(".") / "src"
    outputDir: Path = Path(".") / "dist" / "docs"

    def cmd(self, project: Project) -> str:
        return f"""
. {self.venvPath}/bin/activate &&
pdoc {self.srcPath} --html --force --output-dir {self.outputDir} &&
mv {self.outputDir}/{to_module_name(project.name)}/* {self.outputDir}
"""


class DocStep(PipelineStep):
    config: DocStepConfig
    id: str = "doc"

    run: RunImplicit = lambda self, project, flow_id, ctx: self.config.cmd(project)

    sources: SourcesFctImplicit = lambda self, project, flow_id, step_id: FileListing(
        include=[f"src/{project.name.replace('-', '_')}"]
    )

    artifacts: List[Artifact] = [
        Artifact(
            id="docs",
            files=FileListing(
                include=["dist/docs"],
            ),
            links=[Link(name="documentation", url="dist/docs/index.html")],
        )
    ]


class UnitTestStep(PipelineStep):
    id: str = "unit-test"

    run: RunImplicit = (
        lambda self, project, flow_id, ctx: f". ./src/.virtualenv/bin/activate && "
        f"pytest --cov=src/{to_module_name(project.name)} "
        "--cov-report=html:dist/tests/html_dir"
    )

    artifacts: List[Artifact] = [
        Artifact(
            id="test-coverage",
            files=FileListing(
                include=["dist/tests/html_dir"],
            ),
            links=[Link(name="Coverage", url="dist/tests/html_dir/index.html")],
        )
    ]

    sources: SourcesFctImplicit = lambda self, project, flow_id, step_id: FileListing(
        include=[f"src/{to_module_name(project.name)}", "src/tests"]
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
    return {"hosts[0].host": host}


class PipelineConfig(BaseModel):
    tags: List[str] = []
    docConfig: DocStepConfig
    dockerConfig: PublishDockerStepConfig
    helmConfig: InstallHelmStepConfig


async def pipeline(config: PipelineConfig, context: Context):
    def add_dry_values(p, c):
        base = (
            config.helmConfig.overridingHelmValues(p, c)
            if config.helmConfig.overridingHelmValues
            else {}
        )
        return {
            **base,
            "platformDomain": "platform.dev.example.com",
            "clusterVersion": "v1",
        }

    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline", data=config)
        pipeline_env = get_environment()

        dry_run_config = InstallHelmStepConfig(**config.helmConfig.dict())
        dry_run_config.overridingHelmValues = add_dry_values

        install_helm_steps = [
            InstallHelmStep(
                id=f"install-helm_{k8sTarget.name}",
                config=config.helmConfig,
                k8sTarget=k8sTarget,
            )
            for k8sTarget in pipeline_env.helmTargets.targets
        ]

        dags = [
            f"dry-run-helm > install-helm_{k8sTarget.name}"
            for k8sTarget in pipeline_env.helmTargets.targets
        ]

        return Pipeline(
            target=MicroService(),
            tags=["python", "microservice", "fastapi"],
            projectName=lambda path: Path(path).name,
            projectVersion=get_helm_app_version,
            dependencies=lambda project, _ctx: get_dependencies(project),
            steps=[
                PreconditionChecksStep(),
                PullStep(),
                NewBranchStep(),
                UpdatePyYouwolStep(),
                PublishDockerStep(
                    imageVersion=lambda p, _: p.version,
                    dockerRepo=pipeline_env.dockerTarget,
                ),
                SyncHelmDeps(),
                InstallDryRunHelmStep(config=dry_run_config),
                *install_helm_steps,
            ],
            flows=[
                Flow(
                    name="prod",
                    dag=[
                        "checks > pull > new-branch > dry-run-helm",
                        "pull > sync-pyYw > publish-docker > dry-run-helm",
                        "pull > sync-helm-deps > dry-run-helm",
                        *dags,
                    ],
                )
            ],
        )


async def get_backend_apps_yw_pipeline(name: str, context: Context):
    async with context.start(
        action=f"Youwol backend {name} pipeline creation",
        with_attributes={"project": name},
    ) as ctx:  # type: Context
        config = PipelineConfig(
            tags=[name],
            dockerConfig=PublishDockerStepConfig(repoName="gitlab-docker-repo"),
            docConfig=DocStepConfig(),
            helmConfig=InstallHelmStepConfig(namespace="apps"),
        )
        await ctx.info(text="Pipeline config", data=config)
        result = await pipeline(config, ctx)
        await ctx.info(text="Pipeline", data=result)
        return result
