# standard library
import json
import shutil

from base64 import b64encode
from pathlib import Path

# typing
from typing import Dict, NamedTuple

# third parties
import aiohttp

from fastapi import HTTPException

# Youwol application
from youwol.app.environment import ProjectTemplate

# Youwol backends
from youwol.backends.cdn import get_api_key

# Youwol utilities
from youwol.utils import Context
from youwol.utils.utils_paths import sed_inplace, write_json

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm.common import (
    Dependencies,
    FileNames,
    RunTimeDeps,
    Template,
    copy_files_folders,
    generate_webpack_config,
)
from youwol.pipelines.pipeline_typescript_weback_npm.regular import (
    Bundles,
    MainModule,
    PackageType,
    auto_generated_filename,
    extract_npm_dependencies_dict,
    generate_template_py,
    get_externals,
    imTsSrc,
)


class Keys(NamedTuple):
    name = "name"
    version = "version"
    exported_symbol = "exported symbol"


def external_npm_template(folder: Path):
    return ProjectTemplate(
        icon={"tag": "img", "src": imTsSrc},
        type="publish NPM library",
        folder=folder,
        parameters={
            Keys.name: "package's name",
            Keys.version: "package's version",
            Keys.exported_symbol: "usual exported symbol name (leave blank if none)",
        },
        generator=lambda _folder, params, context: generate_external_npm_template(
            folder, params, context
        ),
    )


async def fetch_package_json(name: str, version: str):
    url = f"https://registry.npmjs.org/{name}/{version}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            if response.status == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"The package {name}#{version} is not found in NPM",
                )
            if response.status == 401:
                raise HTTPException(
                    status_code=401,
                    detail=f"You are not authorized to access the package {name}#{version} in NPM",
                )
            raise HTTPException(
                status_code=response.status,
                detail=f"Unable to fetch 'package.json' file from NPM (package '{name}' at version '{version}') : "
                f"{response.reason}",
            )


async def generate_external_npm_template(
    folder: Path, parameters: Dict[str, str], context: Context
):
    async with context.start("Generate external npm project"):
        name, version = parameters[Keys.name], parameters[Keys.version]
        exported_symbol = parameters[Keys.exported_symbol]
        project_folder = folder / name / version

        folder.mkdir(parents=True, exist_ok=True)

        if project_folder.exists():
            raise RuntimeError(f"Folder {folder} already exist")

        project_folder.mkdir(parents=True)
        target_package_json = await fetch_package_json(name, version)
        in_bundle_deps = {name: "{{__version_from_pkg__}}"}
        template = Template(
            path=project_folder,
            version=version,
            type=PackageType.Library,
            name=name,
            shortDescription=target_package_json.get("description", ""),
            inPackageJson={
                "homepage": target_package_json.get("homepage", ""),
                "keywords": target_package_json.get("keywords", []),
            },
            dependencies=Dependencies(
                runTime=RunTimeDeps(includedInBundle=in_bundle_deps), devTime={}
            ),
            bundles=Bundles(
                mainModule=MainModule(
                    entryFile="./index.ts",
                    loadDependencies=[],
                    aliases=[exported_symbol] if exported_symbol else [],
                )
            ),
            userGuide=False,
        )
        generate_template(template)
        shutil.copytree(
            src=project_folder / ".template", dst=project_folder, dirs_exist_ok=True
        )
        generate_template_py(template, "external")
        for pattern, repl in [
            ["__version_from_pkg__", "pkg_json['version']"],
        ]:
            sed_inplace(template.path / "template.py", '"{{' + pattern + '}}"', repl)

        return f"{name}~{version}", project_folder


def generate_template(input_template: Template):
    working_path = input_template.path / ".template"
    if working_path.is_dir():
        shutil.rmtree(path=working_path)

    externals, exported_symbols = get_externals(input_template=input_template)

    Path(working_path).mkdir()
    for file in [
        ".gitignore",
        ".npmignore",
        ".prettierignore",
        "LICENSE",
        "jest.config.ts",
        "tsconfig.json",
        "typedoc.js",
    ]:
        shutil.copyfile(
            Path(__file__).parent.parent / "regular" / "templates" / file,
            working_path / file,
        )

    copy_files_folders(
        working_path=working_path,
        base_template_path=Path(__file__).parent / "templates",
        files=[],
        folders=[".yw_pipeline", "src"],
    )
    for path in [
        working_path / "src" / "index.ts",
        working_path / "src" / "tests" / "install.test.ts",
    ]:
        fill_file(path=path, input_template=input_template)

    generate_package_json(
        working_path=working_path,
        input_template=input_template,
    )
    generate_autogenerated(
        working_path=working_path,
        input_template=input_template,
        externals=externals,
        exported_symbols=exported_symbols,
    )

    generate_readme(working_path=working_path, input_template=input_template)
    generate_webpack_config(
        source=Path(__file__).parent.parent
        / "regular"
        / "templates"
        / "webpack.config.lib.ts",
        working_path=working_path,
        input_template=input_template,
    )


def generate_package_json(working_path: Path, input_template: Template):
    load_main_externals = {
        k: v
        for k, v in input_template.dependencies.runTime.externals.items()
        if k in input_template.bundles.mainModule.loadDependencies
    }
    mandatory_dev_deps = extract_npm_dependencies_dict(
        [
            "@types/node",
            "del-cli",
            "typescript",
            "ts-loader",
            "ts-node",
            "webpack",
            "webpack-bundle-analyzer",
            "webpack-cli",
            "@youwol/webpm-client",
            "@youwol/http-clients",
            "@youwol/prettier-config",
            "@youwol/eslint-config",
            "@youwol/tsconfig",
            "@types/jest",
            "@youwol/jest-preset",
            "isomorphic-fetch",
        ]
    )
    mandatory_fields = {
        "scripts": {
            "clean": "del-cli dist",
            "auto-gen": "python template.py",
            "build": "yarn build:dev",
            "pre-build": "yarn clean",
            "build:dev": "yarn pre-build && webpack --mode development",
            "build:prod": "yarn pre-build && webpack --mode production",
            "test": "jest -i",
            "test-coverage": "jest -i --collect-coverage",
        },
        "prettier": "@youwol/prettier-config",
        "eslintConfig": {"extends": ["@youwol"]},
    }
    values = {
        "name": input_template.name,
        "version": input_template.version,
        "description": input_template.shortDescription,
        "author": input_template.author,
        "main": f"dist/{input_template.name}.js",
        **{**mandatory_fields, **input_template.inPackageJson},
        "dependencies": {
            **input_template.dependencies.runTime.externals,
            **input_template.dependencies.runTime.includedInBundle,
        },
        "devDependencies": {
            **mandatory_dev_deps,
            **input_template.dependencies.devTime,
        },
        "webpm": {
            "dependencies": load_main_externals,
            "aliases": input_template.bundles.mainModule.aliases,
        },
    }
    write_json(values, working_path / FileNames.package_json)
    with open(working_path / FileNames.package_json, "a", encoding="UTF-8") as file:
        file.write("\n")


def generate_readme(working_path: Path, input_template: Template):
    filename = working_path / "README.md"
    shutil.copyfile(
        Path(__file__).parent / "templates" / "README.lib.md",
        working_path / "README.md",
    )

    dev_documentation = (
        "[Developers documentation](https://platform.youwol.com/applications/@youwol/cdn-explorer/latest"
        f"?package={input_template.name})"
    )

    for pattern, repl in [
        ["name", input_template.name],
        ["shortDescription", input_template.shortDescription],
        ["developerDocumentation", dev_documentation],
    ]:
        sed_inplace(filename, "{{" + pattern + "}}", repl)


def fill_file(path: Path, input_template: Template):
    filename = path
    api_version = get_api_key(input_template.version)
    for pattern, repl in [
        ["name", input_template.name],
        ["version", input_template.version],
        ["apiVersion", api_version],
    ]:
        sed_inplace(filename, "{{" + pattern + "}}", repl)


def generate_autogenerated(
    working_path: Path, input_template: Template, externals, exported_symbols
):
    for pattern, repl in [
        ["name", input_template.name],
        ["assetId", b64encode(input_template.name.encode("ascii")).decode("ascii")],
        ["version", input_template.version],
        ["apiVersion", get_api_key(input_template.version)],
        ["shortDescription", input_template.shortDescription],
        ["main-entry-file", input_template.bundles.mainModule.entryFile],
    ]:
        sed_inplace(
            working_path / "src" / auto_generated_filename, "{{" + pattern + "}}", repl
        )

    for pattern, repl in [
        [
            "'{{runTimeDependencies}}'",
            json.dumps(input_template.dependencies.runTime.dict(), indent=4),
        ],
        ["'{{externals}}'", json.dumps(externals, indent=4)],
        ["'{{exportedSymbols}}'", json.dumps(exported_symbols, indent=4)],
    ]:
        sed_inplace(working_path / "src" / auto_generated_filename, pattern, repl)
