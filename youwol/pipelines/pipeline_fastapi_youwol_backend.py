import os
from pathlib import Path
from typing import Union, List, Optional, Set, Callable

import pkg_resources
from pydantic import BaseModel

from youwol.configuration.models_config import K8sCluster
from youwol.environment.models_project import Manifest, PipelineStepStatus, Link, Flow, \
    SourcesFctImplicit, Pipeline, Skeleton, SkeletonParameter, PipelineStep, FileListing, \
    Artifact, Project, RunImplicit, FlowId, ExplicitNone
from youwol.exceptions import CommandException
from youwol.pipelines.deploy_service import HelmPackage
from youwol.pipelines.publish_cdn import PublishCdnRemoteStep, PublishCdnLocalStep
from youwol.utils.k8s_utils import get_cluster_info
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_yaml


def create_skeleton(path: Union[Path, str]):
    async def generate():
        return

    return Skeleton(
        folder=path,
        description="A skeleton of youwol backend service using FastApi",
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
    run: str = 'python -m venv ./src/.virtualenv '\
               '&& source ./src/.virtualenv/bin/activate ' \
               '&& pip install -r requirements.txt'

    async def get_status(self, project: Project, flow_id: str,
                         last_manifest: Optional[Manifest], context: Context) -> PipelineStepStatus:
        if (project.path / 'src' / '.virtualenv').exists():
            return PipelineStepStatus.OK
        return PipelineStepStatus.none


def to_module_name(dir_name: str):
    return dir_name.replace('-', '_')


class DocStepConfiguration(BaseModel):
    venvPath: Path = Path('.') / 'src' / '.virtualenv'
    srcPath: Path = Path('.') / 'src'
    outputDir: Path = Path('.') / 'dist' / 'docs'

    def cmd(self, project: Project) -> str:
        return f"""
. {self.venvPath}/bin/activate && 
{self.venvPath}/bin/pdoc {self.srcPath} --html --force --output-dir {self.outputDir} &&
mv {self.outputDir}/{to_module_name(project.name)}/* {self.outputDir}
"""


class DocStep(PipelineStep):
    conf: DocStepConfiguration
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


class PublishDockerStep(PipelineStep):

    id: str = "publish-docker"
    imageUrlBuilder: Callable[[Project, Context], str]

    run: RunImplicit = \
        lambda self, p, flow, ctx: \
        f"docker build -t {self.imageUrlBuilder(p, ctx)}:" \
        f"{get_app_version(p.path)} . " \
        f" && docker push {self.imageUrlBuilder(p, ctx)}:{get_app_version(p.path)}"


class ConfDeploy(BaseModel):
    host: str
    open_id_host: str
    secret_youwol_auth: Path
    secret_gitlab_docker: Path


def get_chart_explorer(chart_folder: Path):

    explorer = {}
    for root, folders, files in os.walk(chart_folder):
        parent = Path(root)
        explorer[str(parent)] = {
            "files": [{"name": f, "path": str(chart_folder / parent / f)} for f in files],
            "folders": [{"name": f, "path": str(chart_folder / parent / f)} for f in folders]
        }
    return explorer


class DeployGcStep(PipelineStep):

    namespace: str
    overridingHelmValues: Callable[[Project, Context], dict]
    secrets: dict
    id: str = "deploy-gc"

    run: ExplicitNone = ExplicitNone()

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):

        outputs = []
        context.info(text="")
        async with context.start(
                action="deploy helm chart",
                with_attributes={
                    "namespace": self.namespace
                }) as ctx:

            k8s_info = await get_cluster_info()
            if not k8s_info:
                outputs.append("Can not connect to k8s proxy")
                raise CommandException(command="deploy helm chart", outputs=outputs)

            with_values = self.overridingHelmValues(project, context)
            chart_path = project.path / "chart"
            helm_package = HelmPackage(
                name=project.name,
                namespace=self.namespace,
                chart_folder=chart_path,
                with_values=with_values,
                values_filename='values.yaml',
                secrets=self.secrets,
                chart_explorer=get_chart_explorer(chart_path)
            )

            ctx.send(data=helm_package)
            installed = await helm_package.is_installed(context=ctx)

            if installed and '-next' in project.version:
                outputs.append("Mutable version used, proceed to chart uninstall")
                await helm_package.uninstall(context=ctx)
                installed = False

            if installed:
                outputs.append(f"Helm chart already installed, proceed to chart upgrade")
                ctx.info(text=f"Start helm chart install")
                return_code, cmd, outputs_bash = await helm_package.upgrade(context=ctx)
                outputs = outputs + [cmd] + outputs_bash
                if return_code > 0:
                    raise CommandException(command="deploy helm chart", outputs=outputs)

            if not installed:
                outputs.append(f"Helm chart not already installed, start helm chart install")
                ctx.info(text=f"Start helm chart install")
                return_code, cmd, outputs_bash = await helm_package.install(context=ctx)
                outputs = outputs + [cmd] + outputs_bash
                if return_code > 0:
                    raise CommandException(command="deploy helm chart", outputs=outputs)

        return outputs


def get_version(path: Path):
    return parse_yaml(path / 'chart' / "Chart.yaml")['version']


def get_app_version(path: Path):
    return parse_yaml(path / 'chart' / "Chart.yaml")['appVersion']


def get_ingress(host: str):
    return {
        "hosts[0].host": host
        # "annotations": { "konghq.com/plugins": "oidc-dev" if developers_only else "oidc-user"}
        }


def pipeline(
        docker_repo_name: str,
        k8s_cluster: K8sCluster,
        doc_conf: DocStepConfiguration = DocStepConfiguration()
):
    docker_repo = next((repo for repo in k8s_cluster.docker.repositories if repo.name == docker_repo_name), None)
    docker_secret_name = parse_yaml(docker_repo.pullSecret)['metadata']['name']
    auth_secret_name = parse_yaml(k8s_cluster.openIdConnect.authSecret)['metadata']['name']
    return Pipeline(
        id=__name__,
        language="python",
        projectName=lambda path: Path(path).name,
        projectVersion=lambda path: get_version(path),
        dependencies=lambda project, ctx: get_dependencies(project),
        skeleton=lambda ctx: create_skeleton(ctx),
        steps=[
            PreconditionChecksStep(),
            InitStep(),
            DocStep(conf=doc_conf),
            UnitTestStep(),
            ApiTestStep(),
            IntegrationTestStep(),
            PublishCdnLocalStep(packagedArtifacts=['docs', 'test-coverage']),
            PublishCdnRemoteStep(),
            PublishDockerStep(
                imageUrlBuilder=docker_repo.imageUrlBuilder
            ),
            DeployGcStep(
                namespace='prod',
                overridingHelmValues=lambda project, context: {
                    "image": {
                        "repository": f"{docker_repo.imageUrlBuilder(project, context)}",
                        "tag": get_app_version(project.path)
                    },
                    "imagePullSecrets[0].name": docker_secret_name,
                    "ingress": get_ingress(host=k8s_cluster.host),
                    "keycloak": {
                        "host": k8s_cluster.openIdConnect.host
                    },
                },
                secrets={
                    auth_secret_name: k8s_cluster.openIdConnect.authSecret,
                    docker_secret_name: docker_repo.pullSecret
                }
            )
        ],
        flows=[
            Flow(
                name="prod",
                dag=[
                    "checks > init > unit-test > integration-test > publish-docker > deploy-gc > api-test ",
                    "init > doc ",
                    "unit-test > publish-local > publish-remote"
                ]
            )
        ]
    )
