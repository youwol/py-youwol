# standard library
import functools
import glob
import itertools
import shutil

from pathlib import Path

# typing
from typing import Awaitable, Callable, Dict, List, NamedTuple, Union, cast

# third parties
import pyparsing
import semantic_version

# Youwol application
from youwol.app.routers.projects.models_project import PipelineStep
from youwol.app.routers.system.router import Log
from youwol.app.test.utils_test import PyYouwolSession, TestFailureResult

# Youwol backends
from youwol.backends.cdn import get_api_key
from youwol.backends.cdn.loading_graph_implementation import exportedSymbols

# Youwol utilities
from youwol.utils import JSON, parse_json, write_json
from youwol.utils.context import Context
from youwol.utils.utils_paths import sed_inplace

# Youwol pipelines
from youwol.pipelines import PublishCdnRemoteStep
from youwol.pipelines.pipeline_typescript_weback_npm.environment import get_environment

# relative
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
            **package_json["devDependencies"],
            **(
                {}
                if input_template.type == PackageType.Library
                else package_json_app["devDependencies"]
            ),
        },
        "youwol": {"cdnDependencies": load_main_externals},
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


async def create_sub_pipelines_publish_cdn(start_step: str, context: Context):
    targets = get_environment().cdnTargets
    steps = [
        PublishCdnRemoteStep(id=f"cdn_{cdn_target.name}", cdnTarget=cdn_target)
        for cdn_target in targets
    ]
    dags = [f"{start_step} > cdn_{cdn_target.name}" for cdn_target in targets]
    await context.info(
        text="Cdn pipelines created",
        data={"targets:": targets, "steps": steps, "dags": dags},
    )
    return steps, dags


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
        start_step=start_step, context=context
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


async def yarn_errors_formatter(
    py_yw_session: PyYouwolSession,
    outputs: List[str],
    py_yw_logs_getter: Callable[[PyYouwolSession, File, Test], Awaitable[List[Log]]],
) -> List[TestFailureResult]:
    """
    This function extract relevant information from jest outputs in terms of logs.
    A list of TestFailure is returned, each one related to a particular test in a particular file.
    One test failure gather:
        * a summary of the failure as printed by jest
        * eventually the list of py-youwol logs

    The way py-youwol logs are retrieved is in charge to the caller via the argument 'py_yw_logs_getter'.

    :param py_yw_session: PyYouwol session
    :param outputs: full std outputs of jest
    :param py_yw_logs_getter: callback
    :return:
    """
    lines = itertools.chain.from_iterable(line.split("\n") for line in outputs)
    lines = [line for line in lines if line != ""]
    test_suites_failed = [
        i for i, line in enumerate(lines) if "FAIL src/tests/" in line
    ] + [len(lines)]

    def extract_test_suite(test_file, chunk):
        test_name = chunk[0].split("● ")[1]
        return TestFailureResult(
            name=[test_file.split("/")[-1], test_name],
            py_youwol_logs=py_yw_logs_getter(py_yw_session, test_file, test_name),
            output_summary=chunk,
        )

    def extract_test_file(start, end):
        lines_test = lines[start:end]
        starts = [
            i
            for i, line in enumerate(lines_test)
            if "●" in line and "Console" not in line
        ]
        chunks = [lines_test[i : i + 15] for i in starts]
        test_file = lines_test[0].split(" ")[1]
        return test_file, chunks

    file_results = [
        extract_test_file(start, end)
        for start, end in zip(test_suites_failed[0:-1], test_suites_failed[1:])
    ]
    return [
        extract_test_suite(test_file, chunk)
        for test_file, test_results in file_results
        for chunk in test_results
    ]
