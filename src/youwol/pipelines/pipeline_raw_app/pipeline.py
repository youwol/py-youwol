# standard library
from pathlib import Path

# typing
from typing import Callable, List, Optional

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
    cdnTargets: List[CdnTarget] = []


def set_environment(environment: Environment = Environment()):
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
    files: FileListing = default_files


class PackageStep(PipelineStep):
    """
    This step does not trigger any action (beside the 'echo').
    Its purpose is to define an artifact 'package' that includes the project's files,
    latter publish by the PublishCdnStep.
    """

    id: str = "package"
    run: str = "echo 'Nothing to do'"

    """
    sources defined the files on which depends the package, all the files by default
    """
    sources: FileListing = default_files

    """
    One artifact is defined, it is called 'package' and contains all the files of the project by default.
    """
    artifacts: List[Artifact] = [Artifact(id="package", files=default_files)]

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

        files_artifacts: List[Path] = await project.get_step_artifacts_files(
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
    packagedArtifacts: List[str] = ["package"]
    packagedFolders: List[str] = []


class PipelineConfig(BaseModel):
    """
    Specifies the configuration of the pipeline
    """

    target: BrowserAppBundle

    with_tags: List[str] = []

    packageConfig: PackageConfig = PackageConfig()

    publishConfig: PublishConfig = PublishConfig()


async def pipeline(config: PipelineConfig, context: Context):
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
