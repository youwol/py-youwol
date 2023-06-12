# standard library
import os

from pathlib import Path

# typing
from typing import Callable, List, NamedTuple, Optional, Union

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import UploadTarget, UploadTargets
from youwol.app.routers.projects.models_project import (
    ExplicitNone,
    FileListing,
    FlowId,
    Manifest,
    PipelineStep,
    PipelineStepStatus,
    Project,
    RunImplicit,
)

# Youwol utilities
from youwol.utils import CommandException, execute_shell_cmd
from youwol.utils.context import Context
from youwol.utils.utils_paths import parse_yaml

# Youwol pipelines
from youwol.pipelines.deploy_service import HelmPackage


class FileNames(NamedTuple):
    helm_values_yaml = "values.yaml"


class PublishDockerStepConfig(BaseModel):
    repoName: str
    imageVersion: Union[
        str, Callable[[Project, Context], str]
    ] = lambda project, _ctx: get_helm_app_version(project.path)
    sources: Optional[FileListing] = None


class DockerRepo(UploadTarget):
    name: str
    imageUrlBuilder: Optional[Callable[[Project, Context], str]]
    host: str

    def get_project_url(self, project: Project, context: Context):
        return (
            self.imageUrlBuilder(project, context)
            if self.imageUrlBuilder
            else f"{self.host}/{project.name}"
        )


class DockerImagesPush(UploadTargets):
    targets: List[DockerRepo] = []

    def get_repo(self, repo_name: str):
        return next(repo for repo in self.targets if repo.name == repo_name)


class PublishDockerStep(PipelineStep):
    dockerRepo: DockerRepo
    id: str = "publish-docker"
    imageVersion: Union[str, Callable[[Project, Context], str]] = "latest"

    sources: FileListing = FileListing(include=["src", "Dockerfile"])

    run: RunImplicit = lambda self, p, flow, ctx: self.docker_build_command(p, ctx)

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        fingerprint, _ = await self.get_fingerprint(
            project=project, flow_id=flow_id, context=context
        )
        if last_manifest.fingerprint != fingerprint:
            await context.info(
                text="Source code outdated",
                data={"actual fp": fingerprint, "saved fp": last_manifest.fingerprint},
            )
            return PipelineStepStatus.outdated

        docker_url = self.dockerRepo.get_project_url(project, context)
        _, outputs = await execute_shell_cmd(
            cmd=f"docker manifest inspect {docker_url}:{project.version}",
            context=context,
        )
        if len(outputs) == 1:
            await context.info(text="Images not published yet")
            return PipelineStepStatus.outdated

        return PipelineStepStatus.OK

    def get_image_version(self, project: Project, context: Context) -> str:
        if isinstance(self.imageVersion, str):
            return self.imageVersion
        return self.imageVersion(project, context)

    def docker_build_command(self, project: Project, context: Context):
        docker_url = self.dockerRepo.get_project_url(project, context)

        image_version = self.get_image_version(project, context)
        return (
            f"docker build -t {project.name} ."
            f" && docker tag {project.name}:latest {docker_url}:latest"
            f" && docker tag {project.name}:latest {docker_url}:{image_version}"
            f" && docker push {docker_url}:latest"
            f" && docker push {docker_url}:{image_version}"
        )


def get_helm_version(path: Path):
    return parse_yaml(path / "chart" / "Chart.yaml")["version"]


def get_helm_app_version(path: Path):
    return parse_yaml(path / "chart" / "Chart.yaml")["appVersion"]


def get_chart_explorer(chart_folder: Path):
    explorer = {}
    for root, folders, files in os.walk(chart_folder):
        parent = Path(root)
        explorer[str(parent)] = {
            "files": [
                {"name": f, "path": str(chart_folder / parent / f)} for f in files
            ],
            "folders": [
                {"name": f, "path": str(chart_folder / parent / f)} for f in folders
            ],
        }
    return explorer


class InstallHelmStepConfig(BaseModel):
    namespace: str
    overridingHelmValues: Callable[[Project, Context], dict] = None
    secrets: List[Path] = []
    id: str = "helm"
    chartPath: Callable[[Project, Context], dict] = (
        lambda project, _ctx: project.path / "chart"
    )
    valuesPath: Callable[[Project, Context], dict] = (
        lambda project, _ctx: project.path / "chart" / FileNames.helm_values_yaml
    )


def get_helm_package(config: InstallHelmStepConfig, project: Project, context: Context):
    with_values = (
        config.overridingHelmValues(project, context)
        if config.overridingHelmValues
        else {}
    )
    chart_path = project.path / "chart"

    return HelmPackage(
        name=project.name,
        namespace=config.namespace,
        chart_folder=chart_path,
        with_values=with_values,
        values_filename=FileNames.helm_values_yaml,
        secrets=config.secrets,
        chart_explorer=get_chart_explorer(chart_path),
    )


class K8sClusterTarget(UploadTarget):
    name: str
    context: str


class HelmChartsTargets(UploadTargets):
    k8sConfigFile: Optional[Path] = None
    targets: List[K8sClusterTarget] = []


class InstallHelmStep(PipelineStep):
    isRunning: bool = False
    id = "install-helm"
    config: InstallHelmStepConfig
    k8sTarget: K8sClusterTarget
    run: ExplicitNone = ExplicitNone()

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        async with context.start(
            action="InstallHelmStep.execute_run",
            with_attributes={"namespace": self.config.namespace},
        ) as ctx:
            helm_package = get_helm_package(
                project=project, config=self.config, context=ctx
            )
            exit_code, cmd, outputs = await helm_package.install_or_upgrade(
                kube_context=self.k8sTarget.context, context=context
            )
            if exit_code != 0:
                raise CommandException(command=cmd, outputs=outputs)

        return outputs

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        async with context.start(
            action="InstallHelmStep.get_status",
            with_attributes={"namespace": self.config.namespace},
        ) as ctx:
            _, outputs = await execute_shell_cmd(
                cmd=f"helm get manifest {project.name} -n {self.config.namespace} "
                f"--kube-context {self.k8sTarget.context}",
                context=ctx,
            )
            await ctx.info("retrieved helm manifest", data={"lines": outputs})
            version_output = next(
                output for output in outputs if "app.kubernetes.io/version:" in output
            )
            version = version_output.split('app.kubernetes.io/version: "')[1][0:-2]
            await ctx.info(f"found deployed chart @version {version}")
            return (
                PipelineStepStatus.OK
                if version == project.version
                else PipelineStepStatus.none
            )


class InstallDryRunHelmStep(PipelineStep):
    id = "dry-run-helm"
    config: InstallHelmStepConfig

    run: ExplicitNone = ExplicitNone()

    sources: FileListing = FileListing(include=["chart"])

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        outputs = []
        await context.info(text="")
        async with context.start(
            action="InstallDryRunHelmStep.execute_run",
            with_attributes={"namespace": self.config.namespace},
        ) as ctx:
            helm_package = get_helm_package(
                config=self.config, project=project, context=context
            )

            _, cmd, outputs_bash = await helm_package.dry_run(context=ctx)
            outputs = outputs + [cmd] + outputs_bash

        return outputs
