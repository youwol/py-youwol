from __future__ import annotations

import asyncio
import itertools
import os
from pathlib import Path
from typing import List, Union, Optional, Awaitable, Iterable

from pydantic import BaseModel

from youwol.configuration.defaults import default_path_projects_dir
from youwol.environment.models import IPipelineFactory
from youwol.environment.models_project import Project
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.utils.utils_low_level import get_object_from_module
from youwol_utils import encode_id
from youwol_utils.context import Context
from youwol_utils.utils_paths import FileListing, matching_files

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
            ProjectLoader.projects_promise = load_projects(
                additional_python_scr_paths=env.pathsBook.additionalPythonScrPaths,
                env=env,
                context=context)
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


async def load_projects(additional_python_scr_paths: List[Path],
                        env: YouwolEnvironment,
                        context: Context
                        ) -> List[Result]:

    async with context.start(
            action="load_projects"
    ) as ctx:   # type: Context
        projects = env.projects
        project_folders = projects.finder(env, ctx) \
            if callable(projects.finder) \
            else default_projects_finder(env=env, root_folders=projects.finder)

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

        print(f"""- list of projects successfully loaded:
{chr(10).join([f"  * {p.name} at {p.path} with pipeline {p.pipeline.tags}" for p in results if isinstance(p, Project)])}
- list of projects that failed to load:
{chr(10).join([f"  * {p.path} : {p.message}" for p in results if not isinstance(p, Project)])}
    """)
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


def default_projects_finder(env: YouwolEnvironment, root_folders: Union[None, Path, List[Path]] = None):

    if not root_folders:
        (Path.home() / default_path_projects_dir).mkdir(exist_ok=True)

    root_folders = [Path.home() / default_path_projects_dir] if not root_folders else root_folders
    root_folders = root_folders if isinstance(root_folders, List) else [root_folders]
    results = [auto_detect_projects(env=env, root_folder=root_folder, ignore=["**/dist", '**/py-youwol'])
               for root_folder in root_folders]

    return itertools.chain.from_iterable(results)


def auto_detect_projects(env: YouwolEnvironment, root_folder: Path, ignore: List[str] = None):

    database_ignore = None
    system_ignore = None
    try:
        database_ignore = env.pathsBook.databases.relative_to(root_folder)
    except ValueError:
        pass
    try:
        system_ignore = env.pathsBook.system.relative_to(root_folder)
    except ValueError:
        pass

    ignore = (ignore or []) + [str(path) for path in [database_ignore, system_ignore] if path]
    file_listing = FileListing(
        include=["**/.yw_pipeline/yw_pipeline.py"],
        ignore=["**/node_modules", "**/.template", "**/.git"] + ignore
    )
    yw_pipelines = matching_files(root_folder, file_listing)
    return [p.parent.parent for p in yw_pipelines]
