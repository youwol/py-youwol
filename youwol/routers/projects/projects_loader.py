from __future__ import annotations

from pathlib import Path
from threading import Thread

from pydantic import BaseModel
from typing import List, Union, Optional

from youwol.routers.projects.models import FailureSyntax, Failure
from youwol.routers.projects.models_project import IPipelineFactory
from youwol.environment import YouwolEnvironment
from youwol.routers.projects.models_project import Project
from youwol.environment.python_dynamic_loader import get_object_from_module
from youwol.web_socket import WsDataStreamer
from youwol_utils import encode_id, log_info
from youwol_utils.context import Context

PROJECT_PIPELINE_DIRECTORY = '.yw_pipeline'

Result = Union[Project, Failure]


class ProjectsLoadingResults(BaseModel):
    results: List[Result]


class ProjectLoader:
    context = Context(logs_reporters=[], data_reporters=[WsDataStreamer()])

    thread: Optional[Thread] = None

    projects_list: List[Project] = []

    @staticmethod
    async def resolve(env: YouwolEnvironment):
        if ProjectLoader.thread:
            ProjectLoader.thread.join()
            ProjectLoader.projects_list = []

        async def on_resolved(update: (List[Path], List[Path])):
            # First element of the update is path of new projects, second is path of removed projects
            new_projects = await load_projects(paths=update[0], env=env, context=ProjectLoader.context)
            remaining_projects = [p for p in ProjectLoader.projects_list if p.path not in update[1]]
            projects = remaining_projects + new_projects
            ProjectLoader.projects_list = projects
            log_info(f"New projects count: {len(projects)}")
            await ProjectLoader.context.send(ProjectsLoadingResults(results=projects))

        ProjectLoader.thread = env.projects.finder.resolve(paths_book=env.pathsBook,
                                                           on_projects_count_update=on_resolved)

    @staticmethod
    async def get_projects(env: YouwolEnvironment, context: Context) -> List[Project]:

        async with context.start("ProjectLoader.get_projects"):
            if not ProjectLoader.thread:
                # If ProjectsFinder return a thread, it means live detection => current results are in sync.
                # otherwise (this branch of 'if') we call explicitly 'resolve' again
                await ProjectLoader.resolve(env=env)
            return ProjectLoader.projects_list

    @staticmethod
    def join():
        if ProjectLoader.thread:
            ProjectLoader.thread.join()


async def load_projects(paths: List[Path], env: YouwolEnvironment, context: Context) -> List[Result]:
    async with context.start(
            action="load_projects"
    ) as ctx:  # type: Context

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


async def get_project(project_path: Path,
                      additional_python_src_paths: List[Path],
                      env: YouwolEnvironment,
                      context: Context) -> Project:
    async with context.start(
            action="get_project",
            with_attributes={"folderName": project_path.name}
    ) as ctx:  # type: Context
        pipeline_factory = get_object_from_module(
            module_absolute_path=project_path / PROJECT_PIPELINE_DIRECTORY / 'yw_pipeline.py',
            object_or_class_name='PipelineFactory',
            object_type=IPipelineFactory,
            additional_src_absolute_paths=additional_python_src_paths
        )
        pipeline = await pipeline_factory.get(env, ctx)
        name = pipeline.projectName(project_path)
        return Project(
            name=name,
            id=encode_id(name),
            publishName=name.split('~')[0],
            version=pipeline.projectVersion(project_path),
            pipeline=pipeline,
            path=project_path
        )
