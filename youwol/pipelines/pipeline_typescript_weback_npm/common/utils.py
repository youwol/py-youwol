import glob
import json
import shutil
from pathlib import Path
from typing import Dict, List, Union

import semantic_version

from youwol.pipelines.pipeline_typescript_weback_npm.common import Template
from youwol.utils.utils_low_level import sed_inplace
from youwol_cdn_backend import get_api_key
from youwol_cdn_backend.loading_graph_implementation import exportedSymbols
from youwol_utils import parse_json, write_json, JSON


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
    values = {
        "name": input_template.name,
        "version": input_template.version,
        "description": input_template.shortDescription,
        "author": input_template.author,
        "homepage": f"https://github.com/{input_template.name.replace('@', '')}#README.md",
        "main": f"dist/{input_template.name}.js",
        "dependencies": {
            **input_template.dependencies.runTime.load,
            **input_template.dependencies.runTime.differed
        },
        "devDependencies": {
            **input_template.dependencies.devTime,
            **package_json['devDependencies']
        },
        "youwol": {
            "cdnDependencies": {name: version for name, version in input_template.dependencies.runTime.load.items()
                                if name not in input_template.dependencies.runTime.includedInBundle
                                }
        }
    }
    write_json({**package_json, **values}, working_path / 'package.json')


def get_imports_from_submodules(input_template: Template, all_runtime_deps: Dict[str, str]):

    def clean_import_name(name):
        return name.replace('\'', '').replace(';', '').replace('"', '').replace('\n', '')

    files = [f for f in glob.glob(str(input_template.path / "src" / "lib" / '**' / '*.ts'), recursive=True)]

    lines = []
    for file in files:
        with open(file, 'r') as fp:
            lines = lines + [line for line in fp.readlines() if 'from \'' in line or 'from "' in line]

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
        print(f"ERROR: some packages' import are not listed in run-time dependencies: {dandling_imports}")
        exit(1)

    imports_from_sub_modules = {k: {"package": v, "path": k.split(v)[1]}
                                for k, v in imports_from_dependencies.items() if k != v}
    return imports_from_sub_modules


def generate_webpack_config(source: Path, working_path: Path, input_template: Template):

    def get_api_version(query):
        spec = semantic_version.NpmSpec(query)
        min_version = next((clause for clause in spec.clause.clauses if clause.operator in ['>=', '==']), None)
        return get_api_key(min_version.target)

    filename = working_path / 'webpack.config.js'
    shutil.copyfile(source, filename)
    v = semantic_version.Version(input_template.version)
    api_version = get_api_key(v)
    externals: Dict[str, Union[str, JSON]] = {}
    all_runtime = {
        **input_template.dependencies.runTime.load,
        **input_template.dependencies.runTime.differed
    }
    externals_runtime = {k: v for k, v in all_runtime.items()
                         if k not in input_template.dependencies.runTime.includedInBundle}
    externals_api_version = {k: get_api_version(v) for k, v in externals_runtime.items()}

    imports_from_sub_modules = get_imports_from_submodules(input_template=input_template, all_runtime_deps=all_runtime)

    for name, dep_api_version in externals_api_version.items():
        symbol_name = name if name not in exportedSymbols else exportedSymbols[name]
        externals[name] = f"{symbol_name}_APIv{dep_api_version}"

    for import_path, sub_module in imports_from_sub_modules.items():
        parts = sub_module['path'].split('/')
        symbol_name = externals[sub_module['package']]
        externals[import_path] = {
            "commonjs": import_path,
            "commonjs2": import_path,
            "root": [symbol_name, *[p for p in parts[1:]]]
        }
    sed_inplace(filename, 'const apiVersion = ""', f'const apiVersion = "{api_version}"')
    sed_inplace(filename, 'const externals = {}', f'const externals = {json.dumps(externals,indent=4)}')
