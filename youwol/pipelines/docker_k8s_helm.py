import os
from pathlib import Path
from typing import Callable, Union, List, Optional

from pydantic import BaseModel
from kubernetes_asyncio import config as k8s_config
from youwol.configuration.models_k8s import DockerRepo
from youwol.environment.models_project import PipelineStep, Project, ExplicitNone, FlowId, RunImplicit, Manifest, \
    PipelineStepStatus, FileListing
from youwol.exceptions import CommandException
from youwol.pipelines.deploy_service import HelmPackage
from youwol.utils.k8s_utils import get_cluster_info
from youwol.utils.utils_low_level import execute_shell_cmd
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_yaml


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

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        fingerprint, _ = await self.get_fingerprint(project=project, flow_id=flow_id, context=context)
        if last_manifest.fingerprint != fingerprint:
            await context.info(text="Source code outdated", data={'actual fp': fingerprint,
                                                                  'saved fp': last_manifest.fingerprint})
            return PipelineStepStatus.outdated

        docker_url = self.dockerRepo.imageUrlBuilder(project, context)
        return_code, outputs = await execute_shell_cmd(
            cmd=f"docker manifest inspect {docker_url}:{project.version}",
            context=context
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
    namespace: str
    overridingHelmValues: Callable[[Project, Context], dict] = None
    secrets: List[Path] = []
    id: str = "helm"
    chartPath: Callable[[Project, Context], dict]
    valuesPath: Callable[[Project, Context], dict]


def get_helm_package(config: InstallHelmStepConfig, project: Project, context: Context):

    with_values = config.overridingHelmValues(project, context) if config.overridingHelmValues else {}
    chart_path = project.path / "chart"

    helm_package = HelmPackage(
        name=project.name,
        namespace=config.namespace,
        chart_folder=chart_path,
        with_values=with_values,
        values_filename='values.yaml',
        secrets=config.secrets,
        chart_explorer=get_chart_explorer(chart_path)
    )
    return helm_package


install_helm_running = False


class InstallHelmStep(PipelineStep):
    isRunning: bool = False
    id = 'install-helm'
    config: InstallHelmStepConfig
    k8sContext: str
    run: ExplicitNone = ExplicitNone()

    async def get_helm_package(self, project: Project, context: Context):

        helm_package = get_helm_package(config=self.config, project=project, context=context)
        await context.send(data=helm_package)
        return helm_package

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        global install_helm_running
        if install_helm_running:
            raise CommandException(command="Deploy helm chart",
                                   outputs=["Helm is already installing a chart, this step can not be parallelize"])
        outputs = []

        def on_enter(_: Context):
            global install_helm_running
            install_helm_running = True

        def on_exit(_):
            global install_helm_running
            install_helm_running = False

        async with context.start(
                action="InstallHelmStep.execute_run",
                on_enter=on_enter,
                on_exit=on_exit,
                with_attributes={
                    "namespace": self.config.namespace
                }) as ctx:
            await k8s_config.load_kube_config(context=self.k8sContext)
            stream = os.popen(f"kubectl config use-context {self.k8sContext}")

            k8s_info = await get_cluster_info()
            if not k8s_info:
                outputs.append("Can not connect to k8s proxy")
                raise CommandException(command="Deploy helm chart", outputs=outputs)
            await ctx.info(
                text="k8s_info",
                data={
                    "k8s context": stream.read(),
                    "k8s info": k8s_info
                }
            )

            helm_package = await self.get_helm_package(project=project, context=ctx)

            installed = await helm_package.is_installed(context=ctx)

            if installed and '-wip' in project.version:
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

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:

        async with context.start(
                action="InstallHelmStep.get_status",
                with_attributes={
                    "namespace": self.config.namespace
                }) as ctx:

            stream = os.popen(f"( kubectl config use-context {self.k8sContext} "
                              f"&& helm get manifest {project.name} -n {self.config.namespace})")
            outputs = stream.read()
            await ctx.info("retrieved helm manifest", data={"lines": outputs})
            version_output = next(output for output in outputs.split('\n') if 'app.kubernetes.io/version:' in output)
            version = version_output.split('app.kubernetes.io/version: "')[1][0:-1]
            await ctx.info(f"found deployed chart @version {version}")
            return PipelineStepStatus.OK if version == project.version else PipelineStepStatus.outdated


class InstallDryRunHelmStep(PipelineStep):
    id = 'dry-run-helm'
    config: InstallHelmStepConfig

    run: ExplicitNone = ExplicitNone()

    sources: FileListing = FileListing(include=["chart"])

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):

        outputs = []
        await context.info(text="")
        async with context.start(
                action="InstallDryRunHelmStep.execute_run",
                with_attributes={
                    "namespace": self.config.namespace
                }) as ctx:

            helm_package = get_helm_package(config=self.config, project=project, context=context)

            return_code, cmd, outputs_bash = await helm_package.dry_run(context=ctx)
            outputs = outputs + [cmd] + outputs_bash

        return outputs
