from __future__ import annotations

# standard library
from pathlib import Path

# typing
from typing import List, Optional, Union

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import ProjectsFinderHandler, YouwolEnvironment
from youwol.app.environment.python_dynamic_loader import get_object_from_module
from youwol.app.web_socket import WsDataStreamer

# Youwol utilities
from youwol.utils import encode_id, log_info
from youwol.utils.context import Context

# relative
from .models import Failure, FailureSyntax
from .models_project import IPipelineFactory, Project

PROJECT_PIPELINE_DIRECTORY = ".yw_pipeline"

Result = Union[Project, Failure]


class ProjectsLoadingResults(BaseModel):
    results: List[Result]


class ProjectLoader:
    context = Context(logs_reporters=[], data_reporters=[WsDataStreamer()])

    handler: Optional[ProjectsFinderHandler] = None

    projects_list: List[Project] = []

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
        log_info(f"New projects count: {len(projects)}")
        await ProjectLoader.context.send(ProjectsLoadingResults(results=projects))

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
        await ProjectLoader.handler.initialize()

    @staticmethod
    async def refresh(context: Context) -> List[Project]:
        async with context.start("ProjectLoader.refresh"):
            await ProjectLoader.handler.refresh()
            return ProjectLoader.projects_list

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
    async with context.start(action="load_projects") as ctx:  # type: Context
        results: List[Result] = []
        for dir_candidate in paths:
            try:
                results.append(await get_project(dir_candidate, [], env, ctx))
            except SyntaxError as e:
                msg = f"Could not load project in dir '{dir_candidate}' because of syntax error : {e.msg} "
                await ctx.error(text=msg)
                print(msg)
                results.append(FailureSyntax(path=str(dir_candidate), message=e.msg))
            except Exception as e:
                msg = f"Could not load project in dir '{dir_candidate}' : {e} "
                await ctx.error(text=msg)
                print(msg)
                results.append(Failure(path=str(dir_candidate), message=str(e)))

        return results


async def get_project(
    project_path: Path,
    additional_python_src_paths: List[Path],
    env: YouwolEnvironment,
    context: Context,
) -> Project:
    async with context.start(
        action="get_project", with_attributes={"folderName": project_path.name}
    ) as ctx:  # type: Context
        pipeline_factory = get_object_from_module(
            module_absolute_path=project_path
            / PROJECT_PIPELINE_DIRECTORY
            / "yw_pipeline.py",
            object_or_class_name="PipelineFactory",
            object_type=IPipelineFactory,
            additional_src_absolute_paths=additional_python_src_paths,
        )
        pipeline = await pipeline_factory.get(env, ctx)
        name = pipeline.projectName(project_path)
        return Project(
            name=name,
            id=encode_id(name),
            publishName=name.split("~")[0],
            version=pipeline.projectVersion(project_path),
            pipeline=pipeline,
            path=project_path,
        )
