import os
from pathlib import Path
from typing import Callable, Union, List

from pydantic import BaseModel

from youwol.configuration.models_k8s import DockerRepo
from youwol.environment.models_project import PipelineStep, Project, ExplicitNone, FlowId, RunImplicit
from youwol.exceptions import CommandException
from youwol.pipelines.deploy_service import HelmPackage
from youwol.utils.k8s_utils import get_cluster_info
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_yaml, FileListing


class PublishDockerStepConfig(BaseModel):
    dockerRepo: DockerRepo
    imageVersion: Union[str, Callable[[Project, Context], str]] = None
    sources: FileListing = None


class PublishDockerStep(PipelineStep):
    dockerRepo: DockerRepo
    id: str = "publish-docker"
    imageVersion: Union[str, Callable[[Project, Context], str]] = "latest"

    sources: FileListing = FileListing(
        include=[f"src", 'Dockerfile']
    )

    run: RunImplicit = lambda self, p, flow, ctx: self.docker_build_command(self.config, p, ctx)

    def get_image_version(self, project: Project, context: Context) -> str:
        if isinstance(self.imageVersion, str):
            return self.imageVersion
        return self.imageVersion(project, context)

    def docker_build_command(self, project: Project, context: Context):
        docker_url = self.dockerRepo.imageUrlBuilder(project, context)

        image_version = self.get_image_version(project, context)
        return f"docker build -t {project.name} ." \
               f" && docker tag {project.name}:latest {docker_url}:latest" \
               f" && docker tag {project.name}:latest {docker_url}:{image_version}" \
               f" && docker push {docker_url}:latest" \
               f" && docker push {docker_url}:{image_version}"


def get_helm_version(path: Path):
    return parse_yaml(path / 'chart' / "Chart.yaml")['version']


def get_helm_app_version(path: Path):
    return parse_yaml(path / 'chart' / "Chart.yaml")['appVersion']


def get_chart_explorer(chart_folder: Path):
    explorer = {}
    for root, folders, files in os.walk(chart_folder):
        parent = Path(root)
        explorer[str(parent)] = {
            "files": [{"name": f, "path": str(chart_folder / parent / f)} for f in files],
            "folders": [{"name": f, "path": str(chart_folder / parent / f)} for f in folders]
        }
    return explorer


class InstallHelmStepConfig(BaseModel):
    namespace: str = "default"
    overridingHelmValues: Callable[[Project, Context], dict] = None
    secrets: List[Path] = []
    id: str = "helm"
    chartPath: Callable[[Project, Context], dict]
    valuesPath: Callable[[Project, Context], dict]


class InstallHelmStep(PipelineStep):
    id = 'install-helm'
    config: InstallHelmStepConfig

    run: ExplicitNone = ExplicitNone()

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):

        outputs = []
        await context.info(text="")
        async with context.start(
                action="HelmStep.execute_run",
                with_attributes={
                    "namespace": self.config.namespace
                }) as ctx:

            k8s_info = await get_cluster_info()
            if not k8s_info:
                outputs.append("Can not connect to k8s proxy")
                raise CommandException(command="Deploy helm chart", outputs=outputs)

            with_values = self.config.overridingHelmValues(project, ctx) if self.config.overridingHelmValues else {}
            chart_path = project.path / "chart"

            helm_package = HelmPackage(
                name=project.name,
                namespace=self.config.namespace,
                chart_folder=chart_path,
                with_values=with_values,
                values_filename='values.yaml',
                secrets=self.config.secrets,
                chart_explorer=get_chart_explorer(chart_path)
            )

            await ctx.send(data=helm_package)
            installed = await helm_package.is_installed(context=ctx)

            if installed and '-next' in project.version:
                outputs.append("Mutable version used, proceed to chart uninstall")
                await helm_package.uninstall(context=ctx)
                installed = False

            if installed:
                outputs.append(f"Helm chart already installed, proceed to chart upgrade")
                await ctx.info(text=f"Start helm chart install")
                return_code, cmd, outputs_bash = await helm_package.upgrade(context=ctx)
                outputs = outputs + [cmd] + outputs_bash
                if return_code > 0:
                    raise CommandException(command="deploy helm chart", outputs=outputs)

            if not installed:
                outputs.append(f"Helm chart not already installed, start helm chart install")
                await ctx.info(text=f"Start helm chart install")
                return_code, cmd, outputs_bash = await helm_package.install(context=ctx)
                outputs = outputs + [cmd] + outputs_bash
                if return_code > 0:
                    raise CommandException(command="deploy helm chart", outputs=outputs)

        return outputs
