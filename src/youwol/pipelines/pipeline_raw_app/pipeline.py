# standard library
from pathlib import Path

# typing
from typing import Callable, Optional

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.projects import (
    Artifact,
    BrowserAppBundle,
    FileListing,
    Flow,
    Manifest,
    Pipeline,
    PipelineStep,
    PipelineStepStatus,
)

# Youwol utilities
from youwol.utils import Context, parse_json

# Youwol pipelines
from youwol.pipelines import (
    CdnTarget,
    PublishCdnLocalStep,
    create_sub_pipelines_publish_cdn,
)


class Environment(BaseModel):
    """
    Specifies the remote CDN targets in which the pipeline publish (using
    [set_environment](@yw-nav-function:youwol.pipelines.pipeline_raw_app.set_environment)).
    """

    cdnTargets: list[CdnTarget] = []
    """
    The list of (remote) CDN targets.
    """


def set_environment(environment: Environment = Environment()):
    """
    Set the global [environment](@yw-nav-class:youwol.pipelines.pipeline_raw_app.Environment) of the pipeline
    (the remote CDN targets).

    Example:

        The pipeline can be configured to publish in custom remote CDN targets from the youwol's configuration file
        as illustrated below:

        ```python hl_lines="37-45"
        from youwol.pipelines import CdnTarget
        from youwol.app.environment import (CloudEnvironment, get_standard_auth_provider, BrowserAuth,
         AuthorizationProvider, PublicClient, PrivateClient, DirectAuth)

        import youwol.pipelines.pipeline_raw_app as pipeline_raw_app


        prod_env = CloudEnvironment(
            envId="prod",
            host="platform.youwol.com",
            authProvider=get_standard_auth_provider("platform.youwol.com"),
            authentications=[BrowserAuth(authId="browser")],
        )  # (1)


        bar_env = CloudEnvironment(
            envId="bar",
            host="platform.bar.com",
            authProvider=AuthorizationProvider(
                openidClient=PublicClient(client_id="openid_client_id"),
                openidBaseUrl="https://platform.bar.com/auth/realms/youwol",
                keycloakAdminClient=PrivateClient(
                    client_id="client_id_to_be_provided",
                    client_secret="client_secret_to_be_provided",
                ),
                keycloakAdminBaseUrl="https://platform.bar.com/auth/admin/realms/youwol",
            ),
            authentications=[
                DirectAuth(
                    authId="foo",
                    userName="foo@bar.com",
                    password="foo-pwd",
                ),
            ],
        )  # (2)

        pipeline_raw_app.set_environment(
            environment=pipeline_raw_app.Environment(
                cdnTargets=[
                    CdnTarget(name="bar", cloudTarget=bar_env, authId="foo"),
                    CdnTarget(name="prod", cloudTarget=prod_env, authId="browser"),
                ]
            )
        )
        ```

        1.  Define the regular `platform.youwol.com` environment authenticated through browser'
        2.  This is a custom environment (managed by keycloak regarding identity & access management),
        hosted on `platform.bar.com`, and authenticated using user-name & password.


    Parameters:
        environment: environment listing the CDNs targets
    """
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment] = Environment


def get_environment() -> Environment:
    return Dependencies.get_environment()


default_files = FileListing(
    include=[
        "*",
        "*/**",
    ],
    ignore=[
        "cdn.zip",
        "./.*",
        ".*/*",
        "**/.*/*",
        "node_modules",
        "**/node_modules",
    ],
)


class PackageConfig(BaseModel):
    """
    Configuration regarding packaging.
    """

    files: FileListing = default_files
    """
    Defines the list of files to package.
    """


class PackageStep(PipelineStep):
    """
    This step does not trigger any action (beside the 'echo').
    """

    id: str = "package"
    """
    The ID of the step.
    """

    run: str = "echo 'Nothing to do'"
    """
    Shell command to execute before packaging
    """

    sources: FileListing = default_files
    """
    Sources of the file.
    """

    artifacts: list[Artifact] = [Artifact(id="package", files=default_files)]
    """
    One artifact is defined, it is called 'package' and contains all the files of the project by default.
    """

    async def get_status(
        self,
        project: "Project",
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        status = await super().get_status(
            project=project,
            flow_id=flow_id,
            last_manifest=last_manifest,
            context=context,
        )
        if status != PipelineStepStatus.OK:
            return status

        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)

        files_artifacts: list[Path] = await project.get_step_artifacts_files(
            flow_id=flow_id, step_id=self.id, context=context
        )
        folder = env.pathsBook.artifacts_step(
            project_name=project.name,
            flow_id=flow_id,
            step_id=self.id,
        )
        root_files = {
            str(Path(f).relative_to(folder)).split("/")[1] for f in files_artifacts
        }
        if "package.json" not in root_files:
            await context.error(
                text=f"The artifacts of the step '{self.id}' needs to include a package.json file"
            )
            return PipelineStepStatus.KO
        required_fields = ["main", "name", "version"]
        pkg_json = parse_json(
            env.pathsBook.artifact(
                project_name=project.name,
                flow_id=flow_id,
                step_id=self.id,
                artifact_id=self.id,
            )
            / "package.json"
        )
        if any(field not in pkg_json for field in required_fields):
            await context.error(
                text=f"The package.json file should include the fields {required_fields}"
            )
            return PipelineStepStatus.KO

        if "cdn.zip" in root_files:
            await context.error(
                text=f"The artifacts of the step '{self.id}' should not include the file 'cdn.zip'"
            )
            return PipelineStepStatus.KO

        return PipelineStepStatus.OK


class PublishConfig(BaseModel):
    packagedArtifacts: list[str] = ["package"]
    packagedFolders: list[str] = []


class PipelineConfig(BaseModel):
    """
    Specifies the configuration of the pipeline
    """

    target: BrowserAppBundle
    """
    Defines the target.
    """

    with_tags: list[str] = []
    """
    The list of tags.
    """

    packageConfig: PackageConfig = PackageConfig()
    """
    Configuration specifying the packaging.
    """

    # Implementation details
    publishConfig: PublishConfig = PublishConfig()


async def pipeline(config: PipelineConfig, context: Context):
    """
    Instantiate the pipeline.

    Parameters:
        config: configuration of the pipeline
        context: current context

    Return:
        The pipeline instance.
    """
    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline", data=config)

        publish_remote_steps, dags = await create_sub_pipelines_publish_cdn(
            start_step="cdn-local", targets=get_environment().cdnTargets, context=ctx
        )
        package_step = PackageStep(
            sources=config.packageConfig.files,
            artifacts=[Artifact(id="package", files=config.packageConfig.files)],
        )
        steps = [
            package_step,
            PublishCdnLocalStep(
                packagedArtifacts=config.publishConfig.packagedArtifacts,
                packagedFolders=config.publishConfig.packagedFolders,
            ),
            *publish_remote_steps,
        ]
        package_json = "package.json"

        def sanity_check(path_folder: Path):
            if not (path_folder / package_json).exists():
                raise RuntimeError(
                    "Your project need to include a 'package.json' file with 'name', 'version',"
                    " 'main' attributes"
                )
            return True

        return Pipeline(
            target=config.target,
            tags=config.with_tags,
            projectName=lambda path: sanity_check(path)
            and parse_json(path / package_json)["name"],
            projectVersion=lambda path: sanity_check(path)
            and parse_json(path / package_json)["version"],
            steps=steps,
            flows=[
                Flow(
                    name="prod",
                    dag=[
                        "package > cdn-local",
                        *dags,
                    ],
                )
            ],
        )
