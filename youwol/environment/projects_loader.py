from __future__ import annotations

import asyncio
import os
from pathlib import Path
from pydantic import BaseModel
from typing import List, Union, Optional, Awaitable, Iterable

from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models import IPipelineFactory
from youwol.environment.models_project import Project
from youwol.utils.utils_low_level import get_object_from_module
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
        if "ProjectLoader" in env.private_cache:
            return env.private_cache["ProjectLoader"]

        if not ProjectLoader.projects_promise:
            ProjectLoader.projects_promise = load_projects(env=env, context=context)
            projects = await ProjectLoader.projects_promise
            env.private_cache["ProjectLoader"] = projects
            ProjectLoader.projects_promise = None
        else:
            projects = None
            for _ in range(10):
                await asyncio.sleep(0.2)
                if env.private_cache.get("ProjectLoader", None):
                    projects = env.private_cache.get("ProjectLoader")
                    break
            if not projects:
                raise RuntimeError("Resolution of already started projects took too long")

        return projects


async def load_projects(env: YouwolEnvironment, context: Context) -> List[Result]:
    async with context.start(
            action="load_projects"
    ) as ctx:  # type: Context
        projects = env.projects
        project_folders = await projects.finder(env, ctx)

        results_dirs = get_projects_dirs_candidates(project_folders)
        candidates_dirs = [
            candidate_dirs
            for candidate_dirs in results_dirs
            if isinstance(candidate_dirs, Path)
        ]
        # await ctx.info(text="Candidates directory", data={"directories": candidates_dirs})
        results: List[Result] = [
            candidate_dirs
            for candidate_dirs in results_dirs
            if not isinstance(candidate_dirs, Path)
        ]
        for dir_candidate in candidates_dirs:
            try:
                results.append(await get_project(dir_candidate, additional_python_scr_paths, env, ctx))
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


def get_projects_dirs_candidates(projects_dirs: Iterable[Path]) -> List[Union[Path, Failure]]:
    def is_project(maybe_path: Path):
        test_path = maybe_path / PROJECT_PIPELINE_DIRECTORY / 'yw_pipeline.py'
        return maybe_path if test_path.exists() else FailureNoPipeline(path=str(maybe_path))

    return [is_project(p) for p in projects_dirs]


def get_projects_dir_candidate(projects_dir) -> List[Union[Path, Failure]]:
    result = []
    if len(os.listdir(projects_dir)) == 0:
        result.append(FailureEmptyDir(path=str(projects_dir)))
    elif (projects_dir / PROJECT_PIPELINE_DIRECTORY).exists():
        # This dir is a project
        result.append(projects_dir)
    else:
        # This dir may contain projects
        for sub_dir in os.listdir(projects_dir):
            sub_dir_path = projects_dir / Path(sub_dir)
            if not sub_dir_path.is_dir():
                continue
            if sub_dir[0] == ".":
                continue
            if (sub_dir_path / PROJECT_PIPELINE_DIRECTORY).exists():
                result.append(sub_dir_path)
            else:
                result.append(FailureNoPipeline(path=str(sub_dir_path)))

    return result


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

