from __future__ import annotations

import asyncio
from pathlib import Path
from pydantic import BaseModel
from typing import List, Union, Optional, Awaitable

from youwol.routers.projects.models_project import IPipelineFactory
from youwol.environment import YouwolEnvironment
from youwol.routers.projects.models_project import Project
from youwol.environment.python_dynamic_loader import get_object_from_module
from youwol_utils import encode_id
from youwol_utils.context import Context

PROJECT_PIPELINE_DIRECTORY = '.yw_pipeline'


class Failure(BaseModel):
    path: str
    failure: str = 'generic'
    message: str


class FailureNoPipeline(Failure):
    failure: str = 'no_pipeline'
    message: str = "No pipeline in directory"


class FailureEmptyDir(Failure):
    failure: str = 'empty_dir'
    message: str = "Directory is empty"


class FailureSyntax(Failure):
    failure: str = 'syntax'


Result = Union[Project, Failure]


class ProjectLoader:
    # This attribute is not none when a promise of projects' result has been started but not yet finished
    # It allows to not fetch projects at the same time
    projects_promise: Optional[Awaitable[List[Result]]] = None

    @staticmethod
    async def get_projects(env: YouwolEnvironment, context: Context) -> List[Project]:
        return [result
                for result in await ProjectLoader.get_results(env, context)
                if isinstance(result, Project)]

    @staticmethod
    async def get_results(env: YouwolEnvironment, context: Context) -> List[Result]:
        if "ProjectLoader" in env.cache_py_youwol:
            return env.cache_py_youwol["ProjectLoader"]

        if not ProjectLoader.projects_promise:
            ProjectLoader.projects_promise = load_projects(env=env, context=context)
            projects = await ProjectLoader.projects_promise
            env.cache_py_youwol["ProjectLoader"] = projects
            ProjectLoader.projects_promise = None
        else:
            projects = None
            for _ in range(10):
                await asyncio.sleep(0.2)
                if env.cache_py_youwol.get("ProjectLoader", None):
                    projects = env.cache_py_youwol.get("ProjectLoader")
                    break
            if not projects:
                raise RuntimeError("Resolution of already started projects took too long")

        return projects


async def load_projects(env: YouwolEnvironment, context: Context) -> List[Result]:
    async with context.start(
            action="load_projects"
    ) as ctx:  # type: Context
        projects = env.projects
        project_folders = await projects.finder(env.pathsBook, ctx)

        results: List[Result] = []
        for dir_candidate in project_folders:
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

