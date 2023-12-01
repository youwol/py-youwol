# standard library
import functools
import glob
import shutil

from pathlib import Path

# typing
from typing import Dict, List, NamedTuple, Union, cast

# third parties
import pyparsing
import semantic_version

# Youwol application
from youwol.app.routers.projects.models_project import PipelineStep

# Youwol backends
from youwol.backends.cdn import get_api_key
from youwol.backends.cdn.loading_graph_implementation import exportedSymbols

# Youwol utilities
from youwol.utils import JSON, parse_json, write_json
from youwol.utils.context import Context
from youwol.utils.utils_paths import sed_inplace

# Youwol pipelines
from youwol.pipelines import create_sub_pipelines_publish_cdn
from youwol.pipelines.pipeline_typescript_weback_npm.environment import get_environment

# relative
from ..common.npm_dependencies_version import extract_npm_dependencies_dict
from .models import PackageType, Template
from .npm_step import PublishNpmStep


class FileNames(NamedTuple):
    package_json = "package.json"


def copy_files_folders(
    working_path: Path,
    base_template_path: Path,
    files: List[Union[str, Path]],
    folders: List[Union[str, Path]],
):
    for file in files:
        shutil.copyfile(src=base_template_path / Path(file), dst=working_path / file)

    for folder in folders:
        shutil.copytree(
            src=base_template_path / Path(folder),
            dst=working_path / folder,
        )


def generate_package_json(source: Path, working_path: Path, input_template: Template):
    package_json = parse_json(source)

    package_json_app = (
        parse_json(source.parent / "package.app.json")
        if input_template.type == PackageType.Application
        else parse_json(source.parent / FileNames.package_json)
    )
    load_main_externals = {
        k: v
        for k, v in input_template.dependencies.runTime.externals.items()
        if k in input_template.bundles.mainModule.loadDependencies
    }

    dev_app_deps_keys = [
        "css-loader",
        "file-loader",
        "html-webpack-plugin",
        "mini-css-extract-plugin",
        "source-map-loader",
        "webpack-dev-server",
    ]
    dev_common_deps = [
        "@types/node",
        "typescript",
        "ts-lib",
        "ts-node",
        "ts-loader",
        "@types/jest",
        "isomorphic-fetch",
        "typedoc",
        "webpack",
        "webpack-cli",
        "webpack-bundle-analyzer",
        "@types/webpack",
        "del-cli",
        "@youwol/prettier-config",
        "@youwol/eslint-config",
        "@youwol/tsconfig",
        "@youwol/jest-preset",
    ]
    dev_deps_keys = (
        [*dev_common_deps, *dev_app_deps_keys]
        if input_template.type == PackageType.Application
        else dev_common_deps
    )
    values = {
        "name": input_template.name,
        "version": input_template.version,
        "description": input_template.shortDescription,
        "author": input_template.author,
        "homepage": f"https://github.com/{input_template.name.replace('@', '')}#README.md",
        "main": f"dist/{input_template.name}.js"
        if input_template.type == PackageType.Library
        else "dist/index.html",
        "dependencies": {
            **input_template.dependencies.runTime.externals,
            **input_template.dependencies.runTime.includedInBundle,
        },
        "devDependencies": {
            **input_template.dependencies.devTime,
            **extract_npm_dependencies_dict(dev_deps_keys),
        },
        "webpm": {
            "dependencies": load_main_externals,
            "aliases": input_template.bundles.mainModule.aliases,
        },
    }
    if input_template.type == PackageType.Application:
        package_json["scripts"] = {
            **package_json["scripts"],
            **package_json_app["scripts"],
        }

    write_json(
        {**package_json, **values, **(input_template.inPackageJson or {})},
        working_path / FileNames.package_json,
    )
    with open(working_path / FileNames.package_json, "a", encoding="UTF-8") as file:
        file.write("\n")


def get_imports_from_submodules(
    input_template: Template, all_runtime_deps: Dict[str, str]
):
    src_folder = "lib" if input_template.type == PackageType.Library else "app"
    base_path = input_template.path / "src" / src_folder

    def clean_import_name(name):
        return name.replace("'", "").replace(";", "").replace('"', "").replace("\n", "")

    lines = []
    for file in glob.glob(str(base_path / "**" / "*.ts"), recursive=True):
        with open(file, "r", encoding="UTF-8") as fp:
            content = fp.read()
            content = pyparsing.cppStyleComment.suppress().transform_string(content)

            lines = lines + [
                line
                for line in content.split("\n")
                if "from '" in line or 'from "' in line
            ]

    imports_from = [clean_import_name(line.split("from ")[-1]) for line in lines]
    packages_imports_from = {line for line in imports_from if line and line[0] != "."}
    print(f"Found imported packages: {packages_imports_from}")
    imports_from_dependencies = {
        clean_import_name(f): next(
            (dep for dep in all_runtime_deps.keys() if f.startswith(dep)), None
        )
        for f in packages_imports_from
    }
    dandling_imports = {
        f
        for f in packages_imports_from
        if not next((dep for dep in all_runtime_deps.keys() if f.startswith(dep)), None)
    }
    if dandling_imports:
        print(
            f"Warning: some packages' import are not listed in run-time dependencies: {dandling_imports}"
        )

    imports_from_sub_modules = {
        k: {"package": v, "path": k.split(v)[1] if v else None}
        for k, v in imports_from_dependencies.items()
        if k != v
    }
    return imports_from_sub_modules


def get_api_version(query):
    spec = semantic_version.NpmSpec(query)
    min_version = next(
        (clause for clause in spec.clause.clauses if clause.operator in [">=", "=="]),
        None,
    )
    return get_api_key(min_version.target)


def get_externals(input_template: Template):
    externals: Dict[str, Union[str, JSON]] = {}
    exported_symbols: Dict[str, JSON] = {}

    all_runtime = {
        **input_template.dependencies.runTime.externals,
        **input_template.dependencies.runTime.includedInBundle,
    }

    externals_runtime = input_template.dependencies.runTime.externals

    externals_api_version = {
        k: get_api_version(v) for k, v in externals_runtime.items()
    }

    imports_from_sub_modules = get_imports_from_submodules(
        input_template=input_template, all_runtime_deps=all_runtime
    )

    for name, dep_api_version in externals_api_version.items():
        symbol_name = name if name not in exportedSymbols else exportedSymbols[name]
        exported_symbols[name] = {
            "apiKey": dep_api_version,
            "exportedSymbol": symbol_name,
        }
        if input_template.type == PackageType.Library:
            externals[name] = {
                "commonjs": name,
                "commonjs2": name,
                "root": f"{symbol_name}_APIv{dep_api_version}",
            }
        else:
            externals[name] = f"window['{symbol_name}_APIv{dep_api_version}']"

    for import_path, sub_module in imports_from_sub_modules.items():
        if (
            not sub_module["package"]
            or import_path in input_template.dependencies.runTime.includedInBundle
        ):
            continue
        parts = sub_module["path"].split("/")
        if input_template.type == PackageType.Library:
            symbol_name = externals[sub_module["package"]]["root"]
            externals[import_path] = {
                "commonjs": import_path,
                "commonjs2": import_path,
                "root": [symbol_name, *parts[1:]],
            }
        else:
            symbol_name = externals[sub_module["package"]]
            path = functools.reduce(
                lambda acc, e: f"{acc}['{e}']", [symbol_name] + parts[1:]
            )
            externals[import_path] = path
    return externals, exported_symbols


def generate_webpack_config(source: Path, working_path: Path, input_template: Template):
    filename = working_path / "webpack.config.ts"
    shutil.copyfile(source, filename)

    if input_template.type == PackageType.Application:
        sed_inplace(
            filename, '"{{devServer.port}}"', str(input_template.devServer.port)
        )


async def create_sub_pipelines_publish_npm(start_step: str, context: Context):
    targets = get_environment().npmTargets
    steps = [
        PublishNpmStep(id=f"npm_{npm_target.name}", npm_target=npm_target)
        for npm_target in targets
    ]
    dags = [f"{start_step} > npm_{npm_target.name}" for npm_target in targets]
    await context.info(
        text="Npm pipelines created",
        data={"targets:": targets, "steps": steps, "dags": dags},
    )
    return steps, dags


async def create_sub_pipelines_publish(start_step: str, context: Context):
    publish_cdn_steps, dags_cdn = await create_sub_pipelines_publish_cdn(
        start_step=start_step, targets=get_environment().cdnTargets, context=context
    )
    publish_npm_steps, dags_npm = await create_sub_pipelines_publish_npm(
        start_step=start_step, context=context
    )

    return (
        cast(List[PipelineStep], publish_cdn_steps) + publish_npm_steps,
        dags_cdn + dags_npm,
    )


File = str
Test = str
