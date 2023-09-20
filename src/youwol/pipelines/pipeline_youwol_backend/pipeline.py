# standard library
from pathlib import Path

# typing
from typing import Iterable, List, Optional, Set

# third parties
import pkg_resources

from pydantic import BaseModel

# Youwol
import youwol

# Youwol application
from youwol.app.routers.projects.models_project import (
    FileListing,
    Flow,
    FlowId,
    Manifest,
    MicroService,
    Pipeline,
    PipelineStep,
    PipelineStepStatus,
    Project,
)

# Youwol utilities
from youwol.utils import matching_files
from youwol.utils.context import Context

# Youwol pipelines
from youwol.pipelines.docker_k8s_helm import (
    InstallDryRunHelmStep,
    InstallHelmStep,
    InstallHelmStepConfig,
    PublishDockerStep,
    PublishDockerStepConfig,
    get_helm_app_name,
    get_helm_app_version,
)
from youwol.pipelines.pipeline_youwol_backend.environment import get_environment


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
    run: str = "echo 'nothing for now'"

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        return PipelineStepStatus.OK


class PublishYwBackendDockerStep(PublishDockerStep):
    backend: str

    async def get_sources(
        self, project: "Project", flow_id: FlowId, context: Context
    ) -> Optional[Iterable[Path]]:
        # missing dockerfile
        yw_root = Path(youwol.app.__file__).parent.parent.parent.parent
        sources = FileListing(
            include=[
                "images/Dockerfile",
                "src/youwol/utils",
                "src/youwol/backends/common",
                f"src/youwol/backends/{self.backend}",
            ],
            ignore=["**/__pycache__"],
        )
        files = matching_files(folder=yw_root, patterns=sources)
        await context.info(text=f"retrieved {len(files)} files for fingerprint")
        return files


class PipelineConfig(BaseModel):
    tags: List[str] = []
    dockerConfig: PublishDockerStepConfig
    helmConfig: InstallHelmStepConfig


async def _pipeline(config: PipelineConfig, context: Context):
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
            projectName=lambda project: get_helm_app_name(
                config.helmConfig.chartPath(project, ctx)
            ),
            projectVersion=lambda project: get_helm_app_version(
                config.helmConfig.chartPath(project, ctx)
            ),
            dependencies=lambda project, _ctx: get_dependencies(project),
            steps=[
                PreconditionChecksStep(),
                PublishYwBackendDockerStep(
                    imageVersion=lambda p, _: p.version,
                    dockerRepo=pipeline_env.dockerTarget,
                    dockerFilePath=config.dockerConfig.dockerFilePath,
                    dockerBuildContextPath=config.dockerConfig.dockerBuildContextPath,
                    buildArgs=config.dockerConfig.buildArgs,
                    backend=config.dockerConfig.buildArgs["backend"],
                ),
                # SyncHelmDeps(),
                InstallDryRunHelmStep(config=dry_run_config),
                *install_helm_steps,
            ],
            flows=[
                Flow(
                    name="prod",
                    dag=[
                        "checks > publish-docker > dry-run-helm",
                        *dags,
                    ],
                )
            ],
        )


async def pipeline(chart_folder: Path, py_youwol_folder: Path, context: Context):
    name: str = get_helm_app_name(chart_folder)
    async with context.start(
        action=f"Youwol backend {name} pipeline creation",
        with_attributes={"project": name},
    ) as ctx:  # type: Context
        config = PipelineConfig(
            tags=[name, "backend"],
            dockerConfig=PublishDockerStepConfig(
                repoName="gitlab-docker-repo",
                imageVersion=lambda project, _ctx: get_helm_app_version(chart_folder),
                dockerBuildContextPath=py_youwol_folder,
                dockerFilePath=py_youwol_folder / "images" / "Dockerfile",
                buildArgs={"backend": name.replace("-", "_")},
            ),
            helmConfig=InstallHelmStepConfig(
                namespace="apps",
                chartPath=lambda project, _ctx: chart_folder,
                valuesPath=lambda project, _ctx: chart_folder / "values.yml",
            ),
        )
        await ctx.info(text="Pipeline config", data=config)
        result = await _pipeline(config, ctx)
        await ctx.info(text="Pipeline", data=result)
        return result
