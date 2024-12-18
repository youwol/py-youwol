# standard library
import functools
import shutil
import time

from collections.abc import Mapping
from pathlib import Path

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
from youwol.app.routers.projects.projects_resolver import ProjectLoader

# Youwol utilities
from youwol.utils import CommandException, execute_shell_cmd, files_check_sum, to_json
from youwol.utils.context import Context
from youwol.utils.utils_paths import copy_tree, list_files, write_json

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
        all_projects = ProjectLoader.projects_list
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
        last_manifest: Manifest | None,
        context: Context,
    ) -> PipelineStepStatus:
        async with context.start(action="get status of project's dependencies") as ctx:
            if not (project.path / "node_modules").exists() or not last_manifest:
                return PipelineStepStatus.NONE

            all_dependencies = flatten_dependencies(project=project)

            diff = DeepDiff(
                all_dependencies, last_manifest.cmdOutputs.get("allDependencies", {})
            )
            if diff:
                await ctx.info(
                    text="dependencies have changed in package.json", data=diff
                )
                return PipelineStepStatus.OUTDATED

            config = await get_project_configuration(
                project_id=project.id, flow_id=flow_id, step_id=self.id, context=ctx
            )
            diff = DeepDiff(config, last_manifest.cmdOutputs.get("config", {}))
            if diff:
                await ctx.info(text="configuration has changed", data=diff)
                return PipelineStepStatus.OUTDATED

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
                return PipelineStepStatus.OUTDATED

            return PipelineStepStatus.OK

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        async with context.start(
            action="run synchronization of workspace dependencies"
        ) as ctx:
            data = await get_input_data(project=project, flow_id=flow_id, context=ctx)
            uid_suffix = (
                f"{int(time.time())}"  # Epoch in s, used to disable yarn's cache
            )
            local_deps_folder = project.path / ".local-dependencies"
            shutil.rmtree(local_deps_folder, ignore_errors=True)
            pkg_json = parse_json(project.path / ".template" / "package.json")
            config = await get_project_configuration(
                project_id=project.id, flow_id=flow_id, step_id=self.id, context=ctx
            )
            to_sync = config.get("synchronizedDependencies", [])

            destination_folders: Mapping[str, Path] = {
                name: project.path / "node_modules" / name for name in data.keys()
            }
            local_packages = []
            for name, p in data.items():
                if name not in to_sync:
                    await ctx.info(text=f"keep original package {name}")
                    continue
                await ctx.info(
                    text=f"sync package {name}",
                    data={
                        "source": p.dist_folder,
                        "destination": destination_folders[name],
                    },
                )
                node_module_path = project.path / "node_modules" / p.project.name
                if node_module_path.exists():
                    await ctx.info(f"Remove {p.project.name} from 'node_modules'")
                    shutil.rmtree(node_module_path)

                await ctx.info(f"Package dependency {p.project.name}")

                return_code_pack, outputs_pack = await execute_shell_cmd(
                    cmd="npm pack", cwd=p.project.path, context=ctx
                )
                if return_code_pack > 0:
                    raise CommandException(command="npm pack", outputs=outputs_pack)
                await ctx.info(f"Successfully packaged {p.project.name}")
                base_name = f"{p.project.name.replace('@', '').replace('/', '-')}-{p.project.version}"
                tgz_to_name = f"{base_name}-{uid_suffix}.tgz"
                tgz_from_name = f"{base_name}.tgz"
                tgz_to_path = local_deps_folder.relative_to(project.path) / tgz_to_name
                await ctx.info(
                    f'Patch "package.json" for local package {tgz_from_name}'
                )

                for k in ["dependencies", "devDependencies"]:
                    if p.project.name in pkg_json.get(k, {}):
                        pkg_json[k][p.project.name] = f"file:{tgz_to_path}"

                resolutions = pkg_json.get("resolutions", {})
                resolutions[p.project.name] = f"file:{tgz_to_path}"
                pkg_json["resolutions"] = resolutions

                local_deps_folder.mkdir(exist_ok=True)
                shutil.move(
                    src=p.project.path / tgz_from_name,
                    dst=local_deps_folder / tgz_to_name,
                )
                local_packages.append(tgz_to_name)

            selected_data = {k: v for k, v in data.items() if k in to_sync}
            all_files = functools.reduce(
                lambda acc, e: acc + e.dist_files, selected_data.values(), []
            )
            write_json(pkg_json, project.path / "package.json")

            install_cmd = f"(cd {project.path} && yarn --check-files)"
            return_code, outputs = await execute_shell_cmd(cmd=install_cmd, context=ctx)
            if return_code > 0:
                raise CommandException(command=install_cmd, outputs=outputs)

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
    def node_module_checksum(project: Project, name: str) -> str | None:
        node_module_folder = project.path / "node_modules" / name
        files = list_files(node_module_folder)
        return files_check_sum(files)
