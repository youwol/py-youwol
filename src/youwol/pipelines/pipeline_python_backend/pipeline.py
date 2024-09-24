# standard library
import re
import shutil

from asyncio.subprocess import Process
from collections.abc import Callable
from pathlib import Path

# third parties
import packaging.version

from fastapi import HTTPException
from pydantic import BaseModel

# Youwol
from youwol import __version__

# Youwol Surrogate for next versions of Python
from youwol.utils.python_next.v3_12 import tomllib

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.environment.proxied_backends import (
    DEFAULT_PARTITION_ID,
    ProxiedBackendConfiguration,
)
from youwol.app.routers.environment.router import emit_environment_status
from youwol.app.routers.projects import (
    Artifact,
    CommandPipelineStep,
    ExplicitNone,
    Family,
    FileListing,
    Flow,
    FlowId,
    Link,
    LinkKind,
    Pipeline,
    PipelineStep,
    Project,
    RunImplicit,
    SourcesFctImplicit,
    Target,
    get_project_configuration,
)

# Youwol utilities
from youwol.utils import (
    PYPROJECT_TOML,
    AnyDict,
    CommandException,
    Context,
    clone_environ,
    execute_shell_cmd,
    find_available_port,
    write_json,
    yw_repo_path,
)

# Youwol pipelines
from youwol.pipelines import (
    Environment,
    PublishCdnLocalStep,
    create_sub_pipelines_publish_cdn,
)


class Dependencies:
    get_environment: Callable[[], Environment] = Environment


def set_environment(environment: Environment = Environment()):
    """
    The environment for this pipeline is only defining the remote ecosystem(s).

    Parameters:
        environment: The environment
    """
    Dependencies.get_environment = lambda: environment


def get_environment() -> Environment:
    return Dependencies.get_environment()


VENV_NAME = ".venv"


class SetupStep(PipelineStep):
    """
    Initializes auto-generated files from `pyproject.toml`:
    *  `/package.json` : defines the packaging for YouWol ecosystem.
    *  `/$PROJECT_NAME/auto_generated.py`: defines runtime accessible information for the backend.
    (`$PROJECT_NAME` is the actual name of the project/package).
    """

    id = "setup"
    """
    ID of the step.

    Warning:
        The flows defined in this pipelines reference this ID, in common scenarios it should not be modified.
    """

    run: ExplicitNone = ExplicitNone()
    """
    The execution of the step is not provided as a shell command, rather it is implemented in the
    function `execute_run` of this class.
    """
    sources: FileListing = FileListing(include=[PYPROJECT_TOML])
    """
    Source files of the step.

    Note:
        If those did not change since last execution, the step is considered in sync.
    """

    async def execute_run(self, project: Project, flow_id: str, context: Context):
        """
        Trigger step execution.

        Parameters:
            project: Project for which the step is executed.
            flow_id: ID of the flow associated.
            context: Current context.

        Return:
            Manifest of the execution
        """
        async with context.start(
            action="SetupStep",
        ):
            shutil.rmtree(project.path / "dist", ignore_errors=True)
            with open(project.path / PYPROJECT_TOML, "rb") as f:
                pyproject = tomllib.load(f)

                package_json = SetupStep.__write_package_json(project, pyproject)
                SetupStep.__write_init_py(project, pyproject)

                return {"package_json": package_json}

    @staticmethod
    def __write_package_json(project: Project, pyproject: AnyDict) -> AnyDict:
        project_name = pyproject["project"]["name"]
        package_json = {
            "name": project_name,
            "version": pyproject["project"]["version"],
            "main": f"dist/{project.name}-{project.version}-py3-none-any.whl",
            "webpm": {"type": "backend"},
        }
        write_json(package_json, project.path / "package.json")
        return package_json

    @staticmethod
    def __write_init_py(project: Project, pyproject: AnyDict) -> None:
        init_file = project.path / pyproject["project"]["name"] / "__init__.py"
        with open(init_file, "r", encoding="utf-8") as file:
            content = file.read()

        with open(init_file, "w", encoding="utf-8") as file:
            patched_version = re.sub(
                r"__version__\s*=\s*[\'\"]([^\'\"]*)[\'\"]",
                f'__version__ = "{pyproject["project"]["version"]}"',
                content,
            )
            default_port = pyproject["youwol"]["default-port"]
            patched_default_port = re.sub(
                r"(__default__port__\s*=\s*)\d+",
                f"__default__port__ = {default_port}",
                patched_version,
            )
            file.write(patched_default_port)


class DependenciesStep(PipelineStep):
    """
    Creates a virtual environment `.venv` in the project's folder and
    installs the project in editable mode.
    """

    id: str = "dependencies"
    """
    ID of the step.

    Warning:
        The flows defined in this pipelines reference this ID, in common scenarios it should not be modified.
    """

    run: ExplicitNone = ExplicitNone()

    sources: FileListing = FileListing(include=[PYPROJECT_TOML, "deps/*"])
    """
    Source files of the step.

    Note:
        If those did not change since last execution, the step is considered in sync.
    """

    async def execute_run(self, project: Project, flow_id: str, context: Context):
        """
        Trigger step execution.

        Parameters:
            project: Project for which the step is executed.
            flow_id: ID of the flow associated.
            context: Current context.

        Return:
            Manifest of the execution
        """

        # for now this is required: 'sudo apt install python3.12-venv'
        async with context.start(
            action="DependenciesStep",
        ) as ctx:
            # this is all temporary until py-youwol#0.1.7 is released
            venv_path = project.path / VENV_NAME
            if venv_path.exists():
                shutil.rmtree(venv_path)

            if packaging.version.parse(__version__).is_devrelease:
                await ctx.info(
                    text="Youwol is a dev release, built and link `yw_clients` from sources"
                )

                (project.path / "deps").mkdir(exist_ok=True)
                yw_clients_path = yw_repo_path() / "lib" / "yw_clients"
                cmd = (
                    f"python3 -m build {yw_clients_path} --wheel && "
                    f"mv {yw_clients_path}/dist/yw_clients-{__version__}*.whl {project.path}/deps"
                )
                await execute_shell_cmd(cmd=cmd, context=context, cwd=project.path)

            cmd = (
                f"(python3 -m venv {VENV_NAME} "
                f"&& . {VENV_NAME}/bin/activate "
                f"&& pip install -e .[dev] --force-reinstall --find-links ./deps)"
            )

            await execute_shell_cmd(cmd=cmd, context=context, cwd=project.path)


async def get_info(project: Project, context: Context):

    async with context.start("get_intput_data") as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        proxy = env.proxied_backends.get_info(
            partition_id=DEFAULT_PARTITION_ID,
            name=project.name,
            query_version=project.version,
        )
        if not proxy:
            raise HTTPException(status_code=404, detail="The backend is not serving")
        return proxy


async def stop_backend(project: Project, context: Context):

    async with context.start("stop_backend") as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        proxy = env.proxied_backends.query_latest(
            partition_id=DEFAULT_PARTITION_ID,
            name=project.name,
            query_version=project.version,
        )
        if proxy:
            await env.proxied_backends.terminate(uid=proxy.uid, context=ctx)
            await emit_environment_status(context=ctx)
            return {"status": "backend terminated"}

        return {"status": "backend or PID not found"}


class CodeQualityStep(PipelineStep):

    id = "quality"

    run: RunImplicit = lambda _step, project, _flow, _ctx: (
        f"(. {VENV_NAME}/bin/activate && "
        f"black ./{project.name} "
        f"&& isort ./{project.name} "
        f"&& pylint ./{project.name} "
        f"&& mypy ./{project.name})"
    )

    sources: SourcesFctImplicit = lambda _step, project, _flow, _ctx: FileListing(
        include=[project.name, PYPROJECT_TOML]
    )


class DocStep(PipelineStep):

    id = "doc"

    run: RunImplicit = lambda _step, project, _flow, _ctx: (
        f"(. {VENV_NAME}/bin/activate && "
        f"pdoc ./{project.name} -d google --output-dir ./dist/docs )"
    )

    sources: SourcesFctImplicit = lambda _step, project, _flow, _ctx: FileListing(
        include=[project.name, PYPROJECT_TOML]
    )

    artifacts: list[Artifact] = [
        Artifact(id="doc", files=FileListing(include=["dist/docs/**"]))
    ]


class RunStep(PipelineStep):
    """
    Starts the service.
    """

    id: str = "run"
    """
    ID of the step.

    Warning:
        The flows defined in this pipelines reference this ID, in common scenarios it should not be modified.
    """

    run: ExplicitNone = ExplicitNone()
    """
    Step execution is defined by the method `execute_run`.
    """
    view: str = Path(__file__).parent / "views" / "run.view.js"
    """
    The view of the step allows to start/stop the underlying service with different options.
    """
    http_commands: list[CommandPipelineStep] = [
        CommandPipelineStep(
            name="get_info",
            do_get=lambda project, flow_id, ctx: get_info(project=project, context=ctx),
        ),
        CommandPipelineStep(
            name="stop_backend",
            do_get=lambda project, flow_id, ctx: stop_backend(
                project=project, context=ctx
            ),
        ),
    ]
    """
    Commands associated to the step:
    *  `get_info` : return the info of associated backend.
    See :meth:`get_info <youwol.app.environment.proxied_backends.BackendsStore.get_info>`.
    *  `stop_backend` : stop the backend proxied from the associated project's name & version.
    """

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        """
        Serve the service and install the proxy.
        """
        async with context.start("run_command") as ctx:
            env = await ctx.get("env", YouwolEnvironment)
            config = await get_project_configuration(
                project_id=project.id, flow_id=flow_id, step_id=self.id, context=ctx
            )
            config = {
                "installDispatch": True,
                "autoRun": True,
                "port": "auto",
                **config,
            }

            port = find_available_port(start=2010, end=3000)
            if config["port"] == "default":
                with open(project.path / PYPROJECT_TOML, "rb") as f:
                    pyproject = tomllib.load(f)
                    port = pyproject["youwol"]["default-port"]

            async def on_executed(process: Process | None, shell_ctx: Context):
                if config["installDispatch"]:
                    env.proxied_backends.register(
                        uid=str(process.pid),
                        partition_id=DEFAULT_PARTITION_ID,
                        name=project.name,
                        version=project.version,
                        configuration=ProxiedBackendConfiguration(),
                        port=port,
                        process=process,
                        install_outputs=["Backend running from sources."],
                        server_outputs_ctx_id=shell_ctx.uid,
                    )
                    await emit_environment_status(context=shell_ctx)
                    await shell_ctx.info(
                        text=f"Dispatch installed from '/backends/{project.name}/{project.version}' "
                        f"to 'localhost:{port}"
                    )
                if process:
                    await shell_ctx.info(
                        text=f"Backend started (pid='{process.pid}') on {port}"
                    )

            if config["autoRun"]:
                shell_cmd = (
                    f"(. {VENV_NAME}/bin/activate "
                    f"&& python {project.name}/main_localhost.py --port={port} --yw_port={env.httpPort})"
                )
                return_code, outputs = await execute_shell_cmd(
                    cmd=shell_cmd,
                    context=ctx,
                    log_outputs=True,
                    on_executed=on_executed,
                    env=clone_environ(env_variables={"PYTHONPATH": str(project.path)}),
                    cwd=project.path,
                )
                if return_code > 0:
                    raise CommandException(command=shell_cmd, outputs=outputs)
                return outputs

            await on_executed(process=None, shell_ctx=ctx)
            return [
                f"Service not started, please serve it manually from the port {port}",
                f"Dispatch installed from '/backends/{project.name}/{project.version}' to 'localhost:{port}",
            ]


default_packaging_files = FileListing(
    include=[
        "*",
        "*/**",
    ],
    ignore=["cdn.zip", "./.*", ".*/*", "**/.*/*", VENV_NAME],
)
"""
Definition of the project's files packaged for publication.
"""


class PackageStep(PipelineStep):
    """
    Creates the artifact `package`, the one that will be published in local or remote ecosystems.
    The `package` artifact includes tarball and wheel of the project as well as the `package.json` & `pyproject.toml`
    files.

    The source files of the step is provided by
    :glob:`default_packaging_files <youwol.pipelines.pipeline_python_backend.pipeline.default_packaging_files>`.
    """

    id: str = "package"
    """
    ID of the step.

    Warning:
        The flows defined in this pipelines reference this ID, in common scenarios it should not be modified.
    """

    run: str = "python -m build"

    sources: FileListing = default_packaging_files
    """
    Source files of the step.

    Note:
        If those did not change since last execution, the step is considered in sync.
    """

    artifacts: list[Artifact] = [
        Artifact(
            id="package",
            files=FileListing(
                include=[
                    "deps/*",
                    "dist/*.whl",
                    "Dockerfile",
                    "start.sh",
                    "install.sh",
                    "package.json",
                    PYPROJECT_TOML,
                ]
            ),
        )
    ]
    """
    One 'package' artifact is defined, it includes tarball and wheel of the project as well as the `package.json` &
    `pyproject.toml` files.
    """


class PipelineConfig(BaseModel):
    """
    Specifies the configuration of the pipeline
    """

    with_tags: list[str] = []
    """
    The list of tags.
    """


async def pipeline(config: PipelineConfig, context: Context):
    """
    Instantiates the pipeline.

    It includes the following steps:
    *  :class:`SetupStep <youwol.pipelines.pipeline_python_backend.pipeline.SetupStep>`:
    Initializes of auto-generated files.
    *  :class:`DependenciesStep <youwol.pipelines.pipeline_python_backend.pipeline.DependenciesStep>`:
    Creates & setups a virtual environment.
    *  :class:`PackageStep <youwol.pipelines.pipeline_python_backend.pipeline.PackageStep>`:
    Packages selected files into a single artifact.
    *  :class:`PublishCdnLocalStep <youwol.pipelines.publish_cdn.PublishCdnLocalStep>`:
    Publishes in the local ecosystem the artifact from the `PackageStep`.
    *  One or more :class:`PublishCdnRemoteStep <youwol.pipelines.publish_cdn.PublishCdnLocalStep>`:
    Publishes in remote ecosystem(s) the package from the local ecosystem.
    *  :class:`RunStep <youwol.pipelines.pipeline_python_backend.pipeline.RunStep>`:
    Runs the service.

    It includes the following flows:
    *  `prod`: `['setup > dependencies > package > cdn-local > *cdn-remote', 'dependencies > run']` where
    `*cdn-remote` are the steps publishing the package in remote ecosystem(s).

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
        dependencies_step = DependenciesStep()
        package_step = PackageStep()
        steps = [
            SetupStep(),
            dependencies_step,
            package_step,
            RunStep(),
            DocStep(),
            CodeQualityStep(),
            PublishCdnLocalStep(
                packagedArtifacts=["package", "doc"],
            ),
            *publish_remote_steps,
        ]

        def parse_toml(project_folder: Path):
            with open(project_folder / PYPROJECT_TOML, "rb") as f:
                return tomllib.load(f)

        return Pipeline(
            target=lambda project: Target(
                family=Family.SERVICE,
                links=[
                    Link(
                        name="Swagger",
                        url=f"/backends/{project.name}/{project.version}/docs",
                        kind=LinkKind.PLAIN_URL,
                    ),
                    Link(name="API-Doc", url="dist/docs/index.html"),
                ],
            ),
            tags=config.with_tags,
            projectName=lambda path: parse_toml(path)["project"]["name"],
            projectVersion=lambda path: parse_toml(path)["project"]["version"],
            steps=steps,
            flows=[
                Flow(
                    name="prod",
                    dag=[
                        "setup > dependencies > package > cdn-local",
                        *dags,
                        "dependencies > run",
                        "dependencies > quality",
                        "dependencies > doc > cdn-local",
                    ],
                )
            ],
        )
