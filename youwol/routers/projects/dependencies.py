
from collections import defaultdict
from typing import List, Dict

from pydantic import BaseModel

from youwol.environment.models_project import Project
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.projects.models import (
    ChildToParentConnections, DependenciesResponse,
)
from youwol_utils.context import Context


async def check_cyclic_dependency(
        project_name: str,
        all_projects: List[Project],
        forbidden: List[str],
        context: Context) -> bool:

    forbidden = forbidden + [project_name]
    package = next((p for p in all_projects if p.name == project_name), None)
    if package is None:
        await context.error(text=f"Project {project_name} not found",
                            data={"allProjects": [p.name for p in all_projects]})
        raise RuntimeError(f"Project {project_name} not found")
    dependencies = await package.get_dependencies(recursive=False, context=context)
    errors = [p for p in dependencies if p.name in forbidden]
    if errors:
        raise RuntimeError(f"Cyclic dependencies detected:\n " +
                           f"{'=>'.join(forbidden[1:] + [project_name] + [errors[0].name])}""")
    for d in dependencies:
        await check_cyclic_dependency(
            project_name=d.name,
            all_projects=all_projects,
            forbidden=forbidden + [project_name],
            context=context
            )
    return True


async def sort_projects(
        projects: List[Project],
        sorted_projects: List[Project],
        context: Context
        ) -> List[Project]:

    sorted_projects = sorted_projects or []
    if not projects:
        return sorted_projects

    sorted_names = [k.name for k in sorted_projects]

    flags = [all(dep.name in sorted_names for dep in await p.get_dependencies(recursive=False, context=context))
             for p in projects]
    remaining = [p for p, f in zip(projects, flags) if not f]

    if all(not f for f in flags):
        for p in projects:
            await check_cyclic_dependency(project_name=p.name, all_projects=projects, forbidden=[], context=context)

    return await sort_projects(
        projects=remaining,
        sorted_projects=sorted_projects + [p for p, f in zip(projects, flags) if f],
        context=context
        )


class ResolvedDependencies(BaseModel):
    global_dag: List[ChildToParentConnections]
    sorted_projects: List[Project]
    recursive_dependencies: Dict[str, List[str]]


async def resolve_workspace_dependencies(context: Context) -> ResolvedDependencies:

    env = await context.get('env', YouwolEnvironment)
    cache = env.cache
    if 'resolved_dependencies' in cache:
        return cache['resolved_dependencies']

    all_projects: List[Project] = env.projects
    parent_ids = defaultdict(lambda: [])
    [parent_ids[d.name].append(project.name)
     for project in all_projects for d in await project.get_dependencies(recursive=False, context=context)]
    for p in all_projects:
        if p.name not in parent_ids:
            parent_ids[p.name] = []

    sorted_projects = await sort_projects(projects=all_projects, sorted_projects=[], context=context)
    deps_rec = {p.name: [d.name for d in await p.get_dependencies(recursive=True, context=context)]
                for p in sorted_projects}
    cache['resolved_dependencies'] = ResolvedDependencies(
        global_dag=[ChildToParentConnections(id=k, parentIds=v) for k, v in parent_ids.items()],
        sorted_projects=sorted_projects,
        recursive_dependencies=deps_rec
        )
    return cache['resolved_dependencies']


async def resolve_project_dependencies(project: Project, context: Context):

    global_deps = await resolve_workspace_dependencies(context=context)

    above = [p.name for p in global_deps.sorted_projects if project.name in global_deps.recursive_dependencies[p.name]]
    below = [p.name for p in global_deps.sorted_projects if p.name in global_deps.recursive_dependencies[project.name]]
    involved = [project.name, *above, *below]

    dag = [ChildToParentConnections(id=d.id, parentIds=[pid for pid in d.parentIds if pid in involved])
           for d in global_deps.global_dag if d.id in involved]
    simple_dag = [
        *[ChildToParentConnections(id=child_name, parentIds=[project.name]) for child_name in below],
        ChildToParentConnections(id=project.name, parentIds=[parent_name for parent_name in above]),
        *[ChildToParentConnections(id=parent_name, parentIds=[])for parent_name in above],
        ]
    return DependenciesResponse(above=above, below=below, dag=dag, simpleDag=simple_dag)
