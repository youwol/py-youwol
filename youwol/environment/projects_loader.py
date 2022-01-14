from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models import IPipelineFactory
from youwol.environment.models_project import Project
from youwol.utils_low_level import get_object_from_module
from youwol_utils import encode_id
from youwol_utils.context import Context

PROJECT_PIPELINE_DIRECTORY = '.yw_pipeline'


class ProjectLoader:
    _projects: Optional[List[Project]] = None

    @staticmethod
    def clear_cache():
        ProjectLoader._projects = None

    @staticmethod
    async def get_projects(env: YouwolEnvironment, context: Context) -> List[Project]:
        if ProjectLoader._projects is None:
            ProjectLoader._projects = \
                await get_projects(projects_dirs=env.pathsBook.projects,
                                   additional_python_scr_paths=env.pathsBook.additionalPythonScrPaths,
                                   env=env,
                                   context=context)

        return ProjectLoader._projects


async def get_projects(projects_dirs: List[Path],
                       additional_python_scr_paths: List[Path],
                       env: YouwolEnvironment,
                       context: Context
                       ) -> List[Project]:
    result = []
    candidates_dirs = get_projects_dirs_candidates(projects_dirs)

    for dir_candidate in candidates_dirs:
        try:
            result.append(await get_project(dir_candidate, additional_python_scr_paths, env, context))
        except SyntaxError as e:
            print(f"Could not load project in dir '{dir_candidate}' because of syntax error : {e.msg} ")
        except Exception as e:
            print(f"Could not load project in dir '{dir_candidate}' : {e} ")

    print(f"""- list of projects:
{chr(10).join([f"  * {p.name} at {p.path} with pipeline {p.pipeline.id}" for p in result])}
    """)
    return result


def get_projects_dirs_candidates(projects_dirs: List[Path]) -> List[Path]:
    result = []
    # For some feedback information
    nb_candidates_overall = 0
    for projects_dir in projects_dirs:
        if (projects_dir / PROJECT_PIPELINE_DIRECTORY).exists():
            # This dir is a project
            result.append(projects_dir)
        else:
            # This dir may contain projects
            for subdir in os.listdir(projects_dir):
                if (projects_dir / Path(subdir) / PROJECT_PIPELINE_DIRECTORY).exists():
                    result.append(projects_dir / Path(subdir))

        # For some feedback information
        nb_candidates_for_dir = len(result) - nb_candidates_overall
        nb_candidates_overall = len(result)
        if nb_candidates_for_dir == 0:
            print(f"No project found in '{projects_dir}'")
        else:
            print(f"found {nb_candidates_for_dir} candidates projects in '{projects_dir}'")

    return result


async def get_project(project_path: Path,
                      additional_python_src_paths: List[Path],
                      env: YouwolEnvironment,
                      context: Context) -> Project:
    pipeline_factory = get_object_from_module(
        module_absolute_path=project_path / PROJECT_PIPELINE_DIRECTORY / 'yw_pipeline.py',
        object_or_class_name='PipelineFactory',
        object_type=IPipelineFactory,
        additional_src_absolute_paths=additional_python_src_paths
    )
    pipeline = await pipeline_factory.get(env, context)
    name = pipeline.projectName(project_path)
    return Project(
        name=name,
        id=encode_id(name),
        version=pipeline.projectVersion(project_path),
        pipeline=pipeline,
        path=project_path
    )
