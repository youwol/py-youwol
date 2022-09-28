import asyncio
import functools
import glob
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Union, Optional

import pyparsing
import semantic_version

from youwol.environment.models_project import PipelineStep, Project, Manifest, PipelineStepStatus, FlowId
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.exceptions import CommandException
from youwol.pipelines import PublishCdnRemoteStep, PackagesPublishYwCdn
from youwol.pipelines.pipeline_typescript_weback_npm.common import NpmRepo
from youwol.pipelines.pipeline_typescript_weback_npm.common import Template, PackageType, PackagesPublishNpm
from youwol.utils.utils_low_level import sed_inplace, execute_shell_cmd
from youwol_cdn_backend import get_api_key
from youwol_cdn_backend.loading_graph_implementation import exportedSymbols
from youwol_utils import parse_json, write_json, JSON
from youwol_utils.context import Context


def copy_files_folders(working_path: Path, base_template_path: Path,
                       files: List[Union[str, Path]], folders: List[Union[str, Path]]):

    for file in files:
        shutil.copyfile(src=base_template_path / Path(file),
                        dst=working_path / file)

    for folder in folders:
        shutil.copytree(src=base_template_path / Path(folder),
                        dst=working_path / folder,
                        )


def generate_package_json(source: Path, working_path: Path, input_template: Template):

    package_json = parse_json(source)
    package_json_app = parse_json(source.parent / 'package.app.json')
    load_main_externals = {k: v for k, v in input_template.dependencies.runTime.externals.items()
                           if k in input_template.bundles.mainModule.loadDependencies}
    values = {
        "name": input_template.name,
        "version": input_template.version,
        "description": input_template.shortDescription,
        "author": input_template.author,
        "homepage": f"https://github.com/{input_template.name.replace('@', '')}#README.md",
        "main": f"dist/{input_template.name}.js" if input_template.type == PackageType.Library else "dist/index.html",
        "dependencies": {
            **input_template.dependencies.runTime.externals,
            **input_template.dependencies.runTime.includedInBundle
        },
        "devDependencies": {
            **input_template.dependencies.devTime,
            **package_json['devDependencies'],
            ** ({} if input_template.type == PackageType.Library else package_json_app['devDependencies'])
        },
        "youwol": {
            "cdnDependencies": load_main_externals
        }
    }
    if input_template.type == PackageType.Application:
        package_json['scripts'] = {**package_json['scripts'], **package_json_app['scripts']}

    write_json({**package_json, **values}, working_path / 'package.json')
    with open(working_path / 'package.json', 'a') as file:
        file.write('\n')


def get_imports_from_submodules(input_template: Template, all_runtime_deps: Dict[str, str]):

    src_folder = "lib" if input_template.type == PackageType.Library else "app"
    base_path = input_template.path / "src" / src_folder

    def clean_import_name(name):
        return name.replace('\'', '').replace(';', '').replace('"', '').replace('\n', '')

    files = [f for f in glob.glob(str(base_path / '**' / '*.ts'), recursive=True)]

    lines = []
    for file in files:
        with open(file, 'r') as fp:
            content = fp.read()
            content = pyparsing.cppStyleComment.suppress().transformString(content)

            lines = lines + [line for line in content.split('\n') if 'from \'' in line or 'from "' in line]

    imports_from = [clean_import_name(line.split("from ")[-1]) for line in lines]
    packages_imports_from = {line for line in imports_from if line and line[0] != '.'}
    print(f"Found imported packages: {packages_imports_from}")
    imports_from_dependencies = {
        clean_import_name(f): next((dep for dep in all_runtime_deps.keys() if f.startswith(dep)), None)
        for f in packages_imports_from
    }
    dandling_imports = {f for f in packages_imports_from
                        if not next((dep for dep in all_runtime_deps.keys() if f.startswith(dep)), None)}
    if dandling_imports:
        print(f"Warning: some packages' import are not listed in run-time dependencies: {dandling_imports}")

    imports_from_sub_modules = {k: {"package": v, "path": k.split(v)[1] if v else None}
                                for k, v in imports_from_dependencies.items() if k != v}
    return imports_from_sub_modules


def get_api_version(query):
    spec = semantic_version.NpmSpec(query)
    min_version = next((clause for clause in spec.clause.clauses if clause.operator in ['>=', '==']), None)
    return get_api_key(min_version.target)


def get_externals(input_template: Template):

    externals: Dict[str, Union[str, JSON]] = {}
    exported_symbols: Dict[str, JSON] = {}

    all_runtime = {**input_template.dependencies.runTime.externals,
                   **input_template.dependencies.runTime.includedInBundle}

    externals_runtime = input_template.dependencies.runTime.externals

    externals_api_version = {k: get_api_version(v) for k, v in externals_runtime.items()}

    imports_from_sub_modules = get_imports_from_submodules(input_template=input_template, all_runtime_deps=all_runtime)

    for name, dep_api_version in externals_api_version.items():
        symbol_name = name if name not in exportedSymbols else exportedSymbols[name]
        exported_symbols[name] = {"apiKey": dep_api_version, "exportedSymbol": symbol_name}
        if input_template.type == PackageType.Library:
            externals[name] = {
                "commonjs": name,
                "commonjs2": name,
                "root":  f"{symbol_name}_APIv{dep_api_version}"
            }
        else:
            externals[name] = f"window['{symbol_name}_APIv{dep_api_version}']"

    for import_path, sub_module in imports_from_sub_modules.items():
        if not sub_module['package'] or import_path in input_template.dependencies.runTime.includedInBundle:
            continue
        parts = sub_module['path'].split('/')
        if input_template.type == PackageType.Library:
            symbol_name = externals[sub_module['package']]['root']
            externals[import_path] = {
                "commonjs": import_path,
                "commonjs2": import_path,
                "root": [symbol_name, *[p for p in parts[1:]]]
            }
        else:
            symbol_name = externals[sub_module['package']]
            path = functools.reduce(lambda acc, e: f"{acc}['{e}']", [symbol_name] + parts[1:])
            externals[import_path] = path
    return externals, exported_symbols


def generate_webpack_config(source: Path, working_path: Path, input_template: Template):

    filename = working_path / 'webpack.config.ts'
    shutil.copyfile(source, filename)

    if input_template.type == PackageType.Application:
        sed_inplace(filename, '"{{devServer.port}}"', str(input_template.devServer.port))


async def get_shasum_published(project: Project, context: Context):
    exit_code, outputs = await execute_shell_cmd(cmd=f'npm view {project.name}@{project.version} dist.shasum',
                                                 context=context)
    return outputs[0].replace('\n', '')


async def get_shasum_local(project: Project, context: Context):
    shasum_prefix = 'shasum:'
    exit_code, outputs = await execute_shell_cmd(cmd=f'(cd {project.path} && npm publish --dry-run)',
                                                 context=context)
    shasum_line = next(line for line in outputs if shasum_prefix in line)
    return shasum_line.split(shasum_prefix)[1].strip()


class PublishNpmStep(PipelineStep):
    id: str = "publish-npm"
    run: str = "yarn publish --access public"
    npm_target: NpmRepo

    async def execute_run(self, project: 'Project', flow_id: FlowId, context: Context):

        async with context.start(
                action="PublishNpmStep.execute_run",
        ) as ctx:
            npm_outputs = await self.npm_target.publish(project=project, context=ctx)
            shasum_published, shasum_local = await asyncio.gather(
                get_shasum_published(project=project, context=context),
                get_shasum_local(project=project, context=context)
            )

            return {
                "npm_outputs": npm_outputs,
                "shasum_published": shasum_published,
                "shasum_local": shasum_local,
                "version": project.version,
                "date": f'{datetime.date.today()}'
            }

    async def get_status(self, project: Project, flow_id: str, last_manifest: Optional[Manifest], context: Context) \
            -> PipelineStepStatus:

        async with context.start(
                action="PublishNpmStep.get_status",
        ) as ctx:
            shasum_prefix = 'shasum:'
            cmd = f"npm view {project.name} versions --json"
            exit_code, outputs = await execute_shell_cmd(cmd=cmd, context=ctx)
            if exit_code != 0:
                raise CommandException(command=cmd, outputs=outputs)
            flat_output = functools.reduce(lambda acc, e: acc+e, outputs, "")
            if f'"{project.version}"' not in flat_output:
                return PipelineStepStatus.none

            exit_code, outputs = await execute_shell_cmd(cmd=f'npm view {project.name}@{project.version} dist.shasum',
                                                         context=ctx)
            shasum_published = outputs[0].replace('\n', '')
            exit_code, outputs = await execute_shell_cmd(cmd=f'(cd {project.path} && npm publish --dry-run)',
                                                         context=ctx)
            shasum_line = next(line for line in outputs if shasum_prefix in line)
            shasum_project = shasum_line.split(shasum_prefix)[1].strip()
            return PipelineStepStatus.OK if shasum_published == shasum_project else PipelineStepStatus.outdated


async def create_sub_pipelines_publish(start_step: str, context: Context):

    env: YouwolEnvironment = await context.get('env', YouwolEnvironment)
    cdn_targets = next(uploadTarget for uploadTarget in env.pipelinesSourceInfo.uploadTargets
                       if isinstance(uploadTarget, PackagesPublishYwCdn))

    publish_cdn_steps: List[PipelineStep] = [PublishCdnRemoteStep(id=f'cdn_{cdn_target.name}',
                                                                  cdnTarget=cdn_target)
                                             for cdn_target in cdn_targets.targets]
    dags_cdn = [f'{start_step} > cdn_{cdn_target.name}' for cdn_target in cdn_targets.targets]

    npm_targets = next(uploadTarget for uploadTarget in env.pipelinesSourceInfo.uploadTargets
                       if isinstance(uploadTarget, PackagesPublishNpm))
    publish_npm_steps: List[PipelineStep] = [PublishNpmStep(id=f'npm_{npm_target.name}', npm_target=npm_target)
                                             for npm_target in npm_targets.targets]

    dags_npm = [f'{start_step} > npm_{npm_target.name}' for npm_target in npm_targets.targets]

    return publish_cdn_steps + publish_npm_steps, dags_cdn + dags_npm
