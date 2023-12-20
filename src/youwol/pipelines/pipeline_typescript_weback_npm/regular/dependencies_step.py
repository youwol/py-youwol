# standard library
import functools
import shutil

from collections.abc import Mapping
from pathlib import Path

# typing
from typing import Optional

# third parties
from deepdiff import DeepDiff

# Youwol application
from youwol.app.environment import PathsBook, YouwolEnvironment
from youwol.app.routers.projects.implementation import get_project_configuration
from youwol.app.routers.projects.models_project import (
    Artifact,
    CommandPipelineStep,
    ExplicitNone,
    FlowId,
    Manifest,
    PipelineStep,
    PipelineStepStatus,
    Project,
    parse_json,
)
from youwol.app.routers.projects.projects_loader import ProjectLoader

# Youwol utilities
from youwol.utils import CommandException, execute_shell_cmd, files_check_sum, to_json
from youwol.utils.context import Context
from youwol.utils.utils_paths import copy_tree, list_files

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm.regular.build_step import BuildStep
from youwol.pipelines.pipeline_typescript_weback_npm.regular.common import Paths
from youwol.pipelines.pipeline_typescript_weback_npm.regular.models import (
    InputDataDependency,
)


def flatten_dependencies(project: Project):
    package_json = parse_json(project.path / Paths.package_json_file)

    return {
        **package_json.get("dependencies", {}),
        **package_json.get("devDependencies", {}),
        **package_json.get("peerDependencies", {}),
    }


def patch_pipeline_generated_module(
    dependency: InputDataDependency, module_path: Path, dist_folder: Path
):
    package_json = parse_json(module_path / "package.json")
    if package_json["types"] == "src/index.ts" and not (dist_folder / "src").exists():
        copy_tree(
            source=dependency.project.path / "src",
            destination=module_path / "src",
            replace=True,
        )


async def get_input_data(project: Project, flow_id: str, context: Context):
    async with context.start(action="get_input_data") as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        all_projects = await ProjectLoader.get_cached_projects()
        dependencies = await project.get_dependencies(
            recursive=True, projects=all_projects, context=ctx
        )
        await ctx.info(
            "Dependencies in workspace retrieved",
            data={
                "dependencies": [d.name for d in dependencies],
                "projectsInWorkspace": [p.name for p in all_projects],
            },
        )
        paths_book: PathsBook = env.pathsBook

        project_step = [
            (
                d,
                next(
                    (
                        s
                        for s in d.get_flow_steps(flow_id=flow_id)
                        if isinstance(s, BuildStep)
                    ),
                    None,
                ),
            )
            for d in dependencies
        ]

        def is_succeeded(p: Project, s: BuildStep):
            manifest = p.get_manifest(flow_id=flow_id, step=s, env=env)
            return manifest.succeeded if manifest else False

        dependencies = [
            (project, step)
            for project, step in project_step
            if step is not None and is_succeeded(project, step)
        ]

        await ctx.info(
            "Succeeded built dependencies in workspace retrieved",
            data={
                "dependencies": [
                    {"projectName": d[0].name, "stepId": d[1].id} for d in dependencies
                ]
            },
        )

        dist_folders = {
            project.name: paths_book.artifact(
                project.name, flow_id, step.id, step.artifacts[0].id
            )
            for project, step in dependencies
        }
        await ctx.info("Source of 'dist' folders retrieved", data=dist_folders)

        dist_files = {name: list_files(folder) for name, folder in dist_folders.items()}
        src_files = {p.name: list_files(p.path / "src") for p, s in dependencies}
        return {
            dependency.name: InputDataDependency(
                project=dependency,
                dist_folder=dist_folders[dependency.name],
                src_folder=dependency.path / "src",
                dist_files=dist_files[dependency.name],
                src_files=src_files[dependency.name],
                checksum=files_check_sum(dist_files[dependency.name]),
            )
            for dependency, step in dependencies
        }


class DependenciesStep(PipelineStep):
    id: str = "dependencies"
    run: ExplicitNone = ExplicitNone()

    artifacts: list[Artifact] = []

    view: str = Path(__file__).parent / "views" / "dependencies.view.js"

    http_commands: list[CommandPipelineStep] = [
        CommandPipelineStep(
            name="get_input_data",
            do_get=lambda project, flow_id, ctx: get_input_data(
                project=project, flow_id=flow_id, context=ctx
            ),
        )
    ]

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        async with context.start(action="get status of project's dependencies") as ctx:
            if not (project.path / "node_modules").exists() or not last_manifest:
                return PipelineStepStatus.none

            all_dependencies = flatten_dependencies(project=project)

            diff = DeepDiff(
                all_dependencies, last_manifest.cmdOutputs.get("allDependencies", {})
            )
            if diff:
                await ctx.info(
                    text="dependencies have changed in package.json", data=diff
                )
                return PipelineStepStatus.outdated

            config = await get_project_configuration(
                project_id=project.id, flow_id=flow_id, step_id=self.id, context=ctx
            )
            diff = DeepDiff(config, last_manifest.cmdOutputs.get("config", {}))
            if diff:
                await ctx.info(text="configuration has changed", data=diff)
                return PipelineStepStatus.outdated

            to_sync = config.get("synchronizedDependencies", [])
            if not to_sync:
                await ctx.info(
                    text="no dependencies to synchronized", data=to_json(last_manifest)
                )
                return PipelineStepStatus.OK

            await ctx.info(text="previous manifest", data=to_json(last_manifest))
            data = await get_input_data(project=project, flow_id=flow_id, context=ctx)
            data = {k: v for k, v in data.items() if k in to_sync}
            prev_checksums = last_manifest.cmdOutputs["checksumsFromDist"]

            synced_dist_artifacts = [
                k
                for k, v in data.items()
                if k in prev_checksums and prev_checksums[k] == v.checksum
            ]
            not_synced_dist_artifacts = [
                k for k, v in data.items() if k not in synced_dist_artifacts
            ]

            await ctx.info(
                text="synchronization of dist artifacts",
                data={
                    "synced": synced_dist_artifacts,
                    "notSynced": not_synced_dist_artifacts,
                },
            )
            if not_synced_dist_artifacts:
                return PipelineStepStatus.outdated

            return PipelineStepStatus.OK

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        async with context.start(
            action="run synchronization of workspace dependencies"
        ) as ctx:
            data = await get_input_data(project=project, flow_id=flow_id, context=ctx)
            existing_modules_to_maybe_sync = [
                name
                for name in data.keys()
                if (project.path / "node_modules" / name).exists()
            ]

            for name in existing_modules_to_maybe_sync:
                shutil.rmtree(project.path / "node_modules" / name)

            install_cmd = f"(cd {project.path} && yarn --check-files)"
            return_code, outputs = await execute_shell_cmd(cmd=install_cmd, context=ctx)
            if return_code > 0:
                raise CommandException(command=install_cmd, outputs=outputs)

            config = await get_project_configuration(
                project_id=project.id, flow_id=flow_id, step_id=self.id, context=ctx
            )
            to_sync = config.get("synchronizedDependencies", [])

            destination_folders: Mapping[str, Path] = {
                name: project.path / "node_modules" / name for name in data.keys()
            }
            for name, p in data.items():
                if name not in to_sync:
                    await ctx.info(text=f"keep original package {name}")
                    continue
                if name in to_sync:
                    await ctx.info(
                        text=f"sync package {name}",
                        data={
                            "source": p.dist_folder,
                            "destination": destination_folders[name],
                        },
                    )
                copy_tree(
                    source=p.dist_folder,
                    destination=destination_folders[name],
                    replace=True,
                )
                patch_pipeline_generated_module(
                    dependency=p,
                    module_path=destination_folders[name],
                    dist_folder=p.dist_folder,
                )

            selected_data = {k: v for k, v in data.items() if k in to_sync}
            all_files = functools.reduce(
                lambda acc, e: acc + e.dist_files, selected_data.values(), []
            )

            return {
                "config": config,
                "yarnInstallOutputs": outputs,
                "syncedModulesFingerprint": files_check_sum(all_files),
                "allDependencies": flatten_dependencies(project=project),
                "checksumsFromDist": {name: d.checksum for name, d in data.items()},
                "actualChecksums": {
                    name: DependenciesStep.node_module_checksum(
                        project=project, name=name
                    )
                    for name in data.keys()
                },
            }

    @staticmethod
    def node_module_checksum(project: Project, name: str) -> Optional[str]:
        node_module_folder = project.path / "node_modules" / name
        files = list_files(node_module_folder)
        return files_check_sum(files)
