from __future__ import annotations

# standard library
import traceback

from pathlib import Path

# typing
from typing import List, Optional, Union

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import ProjectsFinderHandler, YouwolEnvironment
from youwol.app.environment.python_dynamic_loader import (
    ModuleLoadingException,
    get_object_from_module,
)
from youwol.app.web_socket import WsDataStreamer

# Youwol utilities
from youwol.utils import encode_id, log_error, log_info
from youwol.utils.context import Context

# relative
from .models import (
    Failure,
    FailureDirectoryNotFound,
    FailureImportException,
    FailurePipelineNotFound,
)
from .models_project import IPipelineFactory, Project

PROJECT_PIPELINE_DIRECTORY = ".yw_pipeline"

Result = Union[Project, Failure]


class FailuresReport(BaseModel):
    directoriesNotFound: List[FailureDirectoryNotFound] = []
    pipelinesNotFound: List[FailurePipelineNotFound] = []
    importExceptions: List[FailureImportException] = []


class ProjectsLoadingResults(BaseModel):
    results: List[Project]
    failures: FailuresReport


class ProjectLoader:
    context = Context(logs_reporters=[], data_reporters=[WsDataStreamer()])

    handler: Optional[ProjectsFinderHandler] = None

    projects_list: List[Project] = []
    failures_report: FailuresReport = FailuresReport()

    @staticmethod
    def status():
        return ProjectsLoadingResults(
            results=ProjectLoader.projects_list, failures=ProjectLoader.failures_report
        )

    @staticmethod
    async def sync_projects(update: (List[Path], List[Path]), env: YouwolEnvironment):
        # First element of the update is path of new projects, second is path of removed projects
        new_maybe_projects = await load_projects(
            paths=update[0], env=env, context=ProjectLoader.context
        )
        failed = [p for p in new_maybe_projects if not isinstance(p, Project)]
        if failed:
            log_info(f"{len(failed)} projects where not able to load properly")
        new_projects = [p for p in new_maybe_projects if isinstance(p, Project)]
        remaining_projects = [
            p
            for p in ProjectLoader.projects_list
            if p.path not in update[0] + update[1]
        ]
        projects = remaining_projects + new_projects
        ProjectLoader.projects_list = projects
        ProjectLoader.failures_report = FailuresReport(
            directoriesNotFound=[
                p for p in failed if isinstance(p, FailureDirectoryNotFound)
            ],
            pipelinesNotFound=[
                p for p in failed if isinstance(p, FailurePipelineNotFound)
            ],
            importExceptions=[
                p for p in failed if isinstance(p, FailureImportException)
            ],
        )
        log_info(f"New projects count: {len(projects)}")
        await ProjectLoader.context.send(ProjectLoader.status())

    @staticmethod
    async def initialize(env: YouwolEnvironment):
        # This method is called whenever a new YouwolEnvironment is loaded

        async def sync_projects(update: (List[Path], List[Path])):
            return await ProjectLoader.sync_projects(update, env)

        ProjectLoader.stop()

        ProjectLoader.handler = env.projects.finder.handler(
            paths_book=env.pathsBook, on_projects_count_update=sync_projects
        )

        ProjectLoader.projects_list = []
        ProjectLoader.failures_list = []
        await ProjectLoader.handler.initialize()

    @staticmethod
    async def refresh(context: Context) -> ProjectsLoadingResults:
        async with context.start("ProjectLoader.refresh"):
            await ProjectLoader.handler.refresh()
            return ProjectLoader.status()

    @staticmethod
    async def get_cached_projects() -> List[Project]:
        return ProjectLoader.projects_list

    @staticmethod
    def stop():
        if ProjectLoader.handler:
            ProjectLoader.handler.release()


async def load_projects(
    paths: List[Path], env: YouwolEnvironment, context: Context
) -> List[Result]:
    async with context.start(action="load_projects") as ctx:
        return [
            await get_project(dir_candidate, [], env, ctx) for dir_candidate in paths
        ]


async def get_project(
    project_path: Path,
    additional_python_src_paths: List[Path],
    env: YouwolEnvironment,
    context: Context,
) -> Union[Project, Failure]:
    async with context.start(
        action="get_project", with_attributes={"folderName": project_path.name}
    ) as ctx:
        if not project_path.exists():
            error = FailureDirectoryNotFound(path=project_path)
            await ctx.error(text="Can not find project's directory", data=error)
            log_error("Can not find project's directory", {"path": project_path})
            return error

        pipeline_path = project_path / PROJECT_PIPELINE_DIRECTORY / "yw_pipeline.py"

        async def handle_import_error(import_error: FailureImportException):
            import_error_message = "Failed to import project"
            await ctx.error(text=import_error_message, data=import_error)
            log_error(
                import_error_message,
                {"path": str(import_error.path), "message": import_error.message},
            )
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
