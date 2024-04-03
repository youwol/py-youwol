# standard library
import traceback

from pathlib import Path

# typing
from typing import TypeVar, Union

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.environment.python_dynamic_loader import (
    ModuleLoadingException,
    get_object_from_module,
)
from youwol.app.web_socket import WsDataStreamer

# Youwol utilities
from youwol.utils import encode_id, log_info
from youwol.utils.context import Context

# relative
from ..models_project import IPipelineFactory, Project
from .models import (
    Failure,
    FailureDirectoryNotFound,
    FailureImportException,
    FailurePipelineNotFound,
)
from .projects_finder_handlers import GlobalProjectsFinder

PROJECT_PIPELINE_DIRECTORY = ".yw_pipeline"

Result = Union[Project, Failure]


class FailuresReport(BaseModel):
    """
    Describes failures for projects that failed to load.
    """

    directoriesNotFound: list[FailureDirectoryNotFound] = []
    """
    *List[[FailureDirectoryNotFound](@yw-nav-class:youwol.app.routers.projects.models.FailureDirectoryNotFound)]*

    Failure because of a directory not found.
    """
    pipelinesNotFound: list[FailurePipelineNotFound] = []
    """
    *List[[FailurePipelineNotFound](@yw-nav-class:youwol.app.routers.projects.models.FailurePipelineNotFound)]*

    Failure because of a `yw_pipeline.py` file not found.
    """
    importExceptions: list[FailureImportException] = []
    """
    *List[[FailureImportException](@yw-nav-class:youwol.app.routers.projects.models.FailureImportException)]*

    Failure because of an exception while parsing `yw_pipeline.py`.
    """


class ProjectsLoadingResults(BaseModel):
    """
    Describes the status of the projects loaded in the current workspace.
    """

    results: list[Project]
    """
    *List[[Project](@yw-nav-class:youwol.app.routers.projects.models_project.Project)]*

    The list of projects that loaded successfully.
    """
    failures: FailuresReport
    """
    *List[[FailuresReport](@yw-nav-class:FailuresReport)]*

    The list of projects that did not loaded successfully.
    """


class ProjectLoader:
    """
    Manages loading and synchronization of projects within the Youwol environment from multiple
    [ProjectsFinderImpl](@yw-nav-class:ProjectsFinderImpl) defined from [ProjectsFinder](@yw-nav-class:ProjectsFinder)
    models from the configuration.

    This class is responsible for loading, updating, and synchronizing projects based on changes detected in
    the filesystem or environmental configurations.
    """

    context = Context(logs_reporters=[], data_reporters=[WsDataStreamer()])
    """
    The context used for logging and reporting.
    """
    handler: GlobalProjectsFinder | None = None
    """
    The global projects finder instance.
    """
    projects_list: list[Project] = []
    """
    A list of currently loaded projects.
    """
    failures_report: FailuresReport = FailuresReport()
    """
    A report containing information about failed project operations.
    """

    @staticmethod
    def status():
        """
        Retrieves the current loading status including projects and failures.
        """
        ProjectLoader.projects_list = list(
            {p.path: p for p in ProjectLoader.projects_list}.values()
        )
        return ProjectsLoadingResults(
            results=ProjectLoader.projects_list, failures=ProjectLoader.failures_report
        )

    @staticmethod
    async def sync_projects(
        update: tuple[str, list[Path], list[Path]], env: YouwolEnvironment
    ) -> None:
        """
        Synchronizes projects based on the provided update information. This function is called by
        [ProjectsFinderImpl](@yw-nav-class:ProjectsFinderImpl) when updates in the HD filesystem involving projects
        have been caught.

        Parameters:
            update: (i) a string indicating the name of the
                [ProjectsFinder](@yw-nav-class:models.ProjectsFinder) that discovered  the updates, (ii) a list of
                `Path` objects representing the projects that were added, and (iii) a list of `Path` objects
                representing the projects that were removed.
            env: Current environment.
        """
        handler_name, new_projects, deleted_projects = update
        new_maybe_projects = await load_projects(
            paths=new_projects, env=env, context=ProjectLoader.context
        )
        failed = [p for p in new_maybe_projects if not isinstance(p, Project)]
        log_info(
            f"Projects finder '{handler_name}' : {len(new_maybe_projects) - len(failed)} OK, {len(failed)} KO."
        )

        new_projects = [p for p in new_maybe_projects if isinstance(p, Project)]
        remaining_projects = [
            p
            for p in ProjectLoader.projects_list
            if p.path not in new_projects + deleted_projects
        ]
        projects = remaining_projects + new_projects
        ProjectLoader.projects_list = projects

        t = TypeVar("t")

        def update_failures(sources: list[t], target: type[t]) -> list[t]:
            previous = [
                e
                for e in sources
                if e.path.exists()
                and not next((f for f in failed if f.path == e.path), None)
            ]
            new = [p for p in failed if isinstance(p, target)]
            return previous + new

        failures = ProjectLoader.failures_report
        dir_not_found = update_failures(
            failures.directoriesNotFound, FailureDirectoryNotFound
        )
        pipelines_not_found = update_failures(
            failures.pipelinesNotFound, FailurePipelineNotFound
        )
        import_exceptions = update_failures(
            failures.importExceptions, FailureImportException
        )
        ProjectLoader.failures_report = FailuresReport(
            directoriesNotFound=dir_not_found,
            pipelinesNotFound=pipelines_not_found,
            importExceptions=import_exceptions,
        )
        log_info(f"New projects count: {len(projects)}")
        status = ProjectLoader.status()
        await ProjectLoader.context.send(status)

    @staticmethod
    async def initialize(env: YouwolEnvironment):
        """
        Initializes the project loader with the given Youwol environment.
        This method is called (at least) whenever a new YouwolEnvironment is loaded

        Parameters:
            env: youwol environment
        """

        async def sync_projects(update: (list[Path], list[Path])):
            return await ProjectLoader.sync_projects(update, env)

        ProjectLoader.stop()

        ProjectLoader.handler = GlobalProjectsFinder(
            finders=env.projects.finders,
            paths_book=env.pathsBook,
            on_projects_count_update=sync_projects,
        )

        ProjectLoader.projects_list = []
        ProjectLoader.failures_list = []
        await ProjectLoader.handler.initialize()

    @staticmethod
    async def refresh(context: Context) -> ProjectsLoadingResults:
        """
        Explicit refresh of the project loader, updating the project list based on the current environment.
        The multiple [ProjectsFinderImpl](@yw-nav-class:ProjectsFinderImpl) are triggered to re-index projects.

        Parameters:
            context: Current context.

        Return:
            The projects loaded successfully and the loading failures.
        """
        async with context.start("ProjectLoader.refresh"):
            ProjectLoader.projects_list = []
            ProjectLoader.failures_list = []
            await ProjectLoader.handler.refresh()
            return ProjectLoader.status()

    @staticmethod
    def stop():
        """
        Stops the multiple activated [ProjectsWatcher thread](@yw-nav-class:ProjectsWatcher) owned by this class.
        """
        if ProjectLoader.handler:
            ProjectLoader.handler.release()


async def load_projects(
    paths: list[Path], env: YouwolEnvironment, context: Context
) -> list[Result]:
    async with context.start(action="load_projects") as ctx:
        return [
            await get_project(dir_candidate, [], env, ctx) for dir_candidate in paths
        ]


async def get_project(
    project_path: Path,
    additional_python_src_paths: list[Path],
    env: YouwolEnvironment,
    context: Context,
) -> Project | Failure:
    """
    Retrieves project information and pipeline definition from the specified project directory.

    This function reads the project directory at the given `project_path`, validates its structure, and attempts
    to import the pipeline definition file. Upon successful import, it constructs a Project object representing
    the project, including its pipeline instance.

    Parameters:
        project_path: The path to the project directory.
        additional_python_src_paths: Additional paths to search for Python source files required
            for importing the pipeline definition.
        env: The current youwol environment.
        context: The current context.

    Return:
        An instance of the Project class representing the retrieved project information,
        or a Failure object indicating any encountered errors during the retrieval process.
    """
    async with context.start(
        action="get_project", with_attributes={"folderName": project_path.name}
    ) as ctx:
        if not project_path.exists():
            error = FailureDirectoryNotFound(path=project_path)
            await ctx.error(text="Can not find project's directory", data=error)
            return error

        pipeline_path = project_path / PROJECT_PIPELINE_DIRECTORY / "yw_pipeline.py"
        if not pipeline_path.exists():
            error = FailurePipelineNotFound(path=project_path)
            message = f"Can not find pipeline's definition file '{pipeline_path}'."
            await ctx.error(text=message, data=error)
            return error

        async def handle_import_error(import_error: FailureImportException):
            import_error_message = "Failed to import project"
            await ctx.error(text=import_error_message, data=import_error)
            return import_error

        try:
            pipeline_factory = get_object_from_module(
                module_absolute_path=pipeline_path,
                object_or_class_name="PipelineFactory",
                object_type=IPipelineFactory,
                additional_src_absolute_paths=additional_python_src_paths,
            )
        except ModuleLoadingException as e:
            error = FailureImportException(
                path=project_path,
                message=str(e),
                traceback=e.traceback,
                exceptionType=e.exception_type,
            )
            return await handle_import_error(error)

        try:
            pipeline = await pipeline_factory.get(env, ctx)
            name = pipeline.projectName(project_path)
            version = pipeline.projectVersion(project_path)
            return Project(
                name=name,
                id=encode_id(name),
                publishName=name.split("~")[0],
                version=version,
                pipeline=pipeline,
                path=project_path,
            )
        except Exception as e:
            error = FailureImportException(
                path=project_path,
                message=str(e),
                traceback=traceback.format_exc(),
                exceptionType=type(e).__name__,
            )
            return await handle_import_error(error)
