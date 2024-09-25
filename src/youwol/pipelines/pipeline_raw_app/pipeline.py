# standard library
from collections.abc import Callable
from pathlib import Path

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
    Project,
)

# Youwol utilities
from youwol.utils import Context, parse_json

# Youwol pipelines
from youwol.pipelines import (
    Environment,
    PublishCdnLocalStep,
    create_sub_pipelines_publish_cdn,
)


def set_environment(environment: Environment = Environment()):
    """
    Set the global :class:`environment <youwol.pipelines.publish_cdn.Environment>` of the pipeline
    (the remote CDN targets).

    **Example**

    The pipeline can be configured to publish in custom remote CDN targets from the youwol's configuration file
    as illustrated below:

    <code-snippet language="python">
    from youwol.pipelines import CdnTarget
    from youwol.app.environment import (CloudEnvironment, get_standard_auth_provider, BrowserAuth,
     AuthorizationProvider, PublicClient, PrivateClient, DirectAuth)

    import youwol.pipelines.pipeline_raw_app as pipeline_raw_app

    # Define the regular `platform.youwol.com` environment authenticated through browser'
    prod_env = CloudEnvironment(
        envId="prod",
        host="platform.youwol.com",
        authProvider=get_standard_auth_provider("platform.youwol.com"),
        authentications=[BrowserAuth(authId="browser")],
    )

    # This is a custom environment (managed by keycloak regarding identity & access management),
    # hosted on `platform.bar.com`, and authenticated using user-name & password.
    bar_env = CloudEnvironment(
        envId="bar",
        host="platform.bar.com",
        authProvider=AuthorizationProvider(
            openidClient=PublicClient(client_id="openid_client_id"),
            openidBaseUrl="https://platform.bar.com/auth/realms/youwol",
        ),
        authentications=[
            DirectAuth(
                authId="foo",
                userName="foo@bar.com",
                password="foo-pwd",
            ),
        ],
    )

    pipeline_raw_app.set_environment(
        environment=pipeline_raw_app.Environment(
            cdnTargets=[
                CdnTarget(name="bar", cloudTarget=bar_env, authId="foo"),
                CdnTarget(name="prod", cloudTarget=prod_env, authId="browser"),
            ]
        )
    )
    </code-snippet>

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
"""
The definition of the default files included in the package when running the
:class:`PackageStep <youwol.pipelines.pipeline_raw_app.pipeline.PackageStep>`.
"""


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
    The purpose of this step is to package the sources files into a package artifact, later published to local and
    remote component databases.
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
        project: Project,
        flow_id: str,
        last_manifest: Manifest | None,
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
    """
    Configuration regarding publication in the components' databases.

    By default, it only publishes the `package` artifact created by the
    :class:`PackageStep <youwol.pipelines.pipeline_raw_app.pipeline.PackageStep>`.
    """

    packagedArtifacts: list[str] = ["package"]
    """
    List of packaged artifacts' ID.
    """
    packagedFolders: list[str] = []
    """
    Path of extra folder's (not part of the `packagedArtifacts`) that needs to be included in the published component
     as well. Paths are relative from the project's folder. """


class PipelineConfig(BaseModel):
    """
    Specifies the configuration of the pipeline
    """

    target: BrowserAppBundle
    """
    Defines the target, for instance:

    <code-snippet language="python">
    graphics = BrowserAppGraphics(
        appIcon={ 'class': 'far fa-laugh-beam fa-2x' }
    )
    target=BrowserAppBundle(
        displayName="My application",
        execution=Execution(standalone=True),
        graphics=graphics
    )
    </code-snippet>
    """

    with_tags: list[str] = []
    """
    The list of tags.
    """

    packageConfig: PackageConfig = PackageConfig()
    """
    Configuration of the :class:`PackageStep <youwol.pipelines.pipeline_raw_app.pipeline.PackageStep>`.
    """

    # Implementation details
    publishConfig: PublishConfig = PublishConfig()
    """
    Configuration elements regarding publication in the components' databases.
    """


async def pipeline(config: PipelineConfig, context: Context) -> Pipeline:
    """
    Instantiate the pipeline.

    Parameters:
        config: configuration of the pipeline
        context: current context

    Returns:
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
            tags=["javascript", *config.with_tags],
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
