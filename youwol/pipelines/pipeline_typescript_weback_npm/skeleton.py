import glob
import json
import shutil
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

import semantic_version
from pydantic import BaseModel

from youwol.utils.utils_low_level import sed_inplace, JSON
from youwol_utils import write_json, parse_json


class PackageType(Enum):
    """
    Description whether the package is an application or library
    """
    Library = "Library"
    Application = "Application"


class RunTimeDeps(BaseModel):
    """
    Description of the run-time dependencies of the project.

    Attributes:

    - load : :class:`Dict[str, str]`   Dependencies required at run time to load the package
    - differed : :class:`Dict[str, str]`  Additional dependencies required at some points after load
    - includedInBundle : :class:`List[str]` The dependencies to encapsulates in the package's bundle.

    Note: All dependencies listed in 'load' or 'differed' and not available in YouWol ecosystem must be included in
    'includedInBundle'.
    """
    load: Dict[str, str]
    differed: Dict[str, str] = {}
    includedInBundle: List[str] = []


class Dependencies(BaseModel):
    """
    Description of the dependencies of the package.

    Attributes:

    - runTime : :class:`RunTimeDeps` Dependencies required at run time
    - devTime : :class:`Dict[str, str]`  Additional dependencies required only during development cycles
    """
    runTime: RunTimeDeps
    devTime: Dict[str, str]


class Template(BaseModel):
    """
    This class gather required data to properly set-up skeleton of the various configuration files

    Attributes:

    - path : :class:`Path` The path of the project's folder
    - type : :class:`ModuleTypeInput`  Type of the package (library or application)
    - version : :class:`str` Version of the package
    - name : :class:`str` Name of the package
    - shortDescription : :class:`str` Short description of the package
    - author : :class:`str`  Main author of the package
    - userGuide : :class:`Optional[Union[bool, str]]`  optional link to a user guide using standard URL
    - dependencies : :class:`Dependencies` Dependencies of the package
    - testConfig : :class:`Optional[str]` An url to the test config used by py-youwol for tests, if need be
    """
    path: Path
    type: PackageType
    version: str
    name: str
    shortDescription: str
    author: str
    userGuide: bool
    dependencies: Dependencies
    testConfig: Optional[str]


def generate_template(input_template: Template):

    working_path = input_template.path / '.template'
    if working_path.is_dir():
        shutil.rmtree(path=working_path)
    Path(working_path).mkdir()
    copy_files_folders(working_path=working_path)
    generate_package_json(working_path=working_path, input_template=input_template)
    generate_readme(working_path=working_path, input_template=input_template)
    generate_webpack_config(working_path=working_path, input_template=input_template)
    generate_test_files(working_path=working_path)


def copy_files_folders(working_path: Path):
    for file in ['.gitignore', '.npmignore', '.prettierignore', 'jest.config.js', 'LICENSE', 'tsconfig.json',
                 'typedoc.js']:
        shutil.copyfile(src=Path(__file__).parent / 'templates' / file,
                        dst=working_path / file)

    for folder in ['.yw_pipeline', 'src']:
        shutil.copytree(src=Path(__file__).parent / 'templates' / folder,
                        dst=working_path / folder,
                        )


def generate_package_json(working_path: Path, input_template: Template):

    package_json = parse_json(Path(__file__).parent / 'templates' / 'package.json')
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
    package_json['name'] = input_template.name
    package_json['description'] = input_template
    write_json({**package_json, **values}, working_path / 'package.json')


def generate_readme(working_path: Path, input_template: Template):

    filename = working_path / 'README.md'
    shutil.copyfile(Path(__file__).parent / 'templates' / 'README.lib.md', working_path / 'README.md')

    user_guide = f"[Online user-guide](https://l.youwol.com/doc/{input_template.name})" \
        if input_template.userGuide else ""

    dev_documentation = \
        "[Developers documentation](https://platform.youwol.com/applications/@youwol/cdn-explorer/latest" \
        f"?package={input_template.name})"

    source_github = f"[Source on GitHub](https://github.com/{input_template.name.replace('@','')})"

    package_npm = f"[Package on npm](https://www.npmjs.com/package/{input_template.name})"

    test_config = "Tests require [py-youwol](https://l.youwol.com/doc/py-youwol) to run on port 2001 using " \
                  f"the configuration defined [here]({input_template.testConfig})." \
        if input_template.testConfig else ""

    for pattern, repl in [
        ["name", input_template.name],
        ['shortDescription', input_template.shortDescription],
        ['developerDocumentation', dev_documentation],
        ['npmPackage', package_npm],
        ['sourceGithub', source_github],
        ['userGuide', user_guide],
        ['testConfig', test_config]
    ]:
        sed_inplace(filename, "{{"+pattern+"}}", repl)


def generate_webpack_config(working_path: Path, input_template: Template):
    variants = {
        'lodash': '_',
        'three': 'THREE',
        'typescript': 'ts',
        'three-trackballcontrols': 'TrackballControls',
        'codemirror': 'CodeMirror',
        'highlight.js': 'hljs',
        '@pyodide/pyodide': 'loadPyodide',
        'plotly.js': 'Plotly',
        'jquery': '$',
        'popper.js': 'Popper'
    }

    def get_api_version(query):
        spec = semantic_version.NpmSpec(query)
        min_version = next((clause for clause in spec.clause.clauses if clause.operator == '>='), None)
        mini = min_version.target
        if mini.major == 0:
            return f"0{mini.minor}"
        return f'{mini.major}'

    filename = working_path / 'webpack.config.js'
    shutil.copyfile(Path(__file__).parent / 'templates' / 'webpack.config.lib.js', filename)
    v = semantic_version.Version(input_template.version)

    api_version = f'{v.major}' if v.major > 0 else f'0{v.minor}'
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
        symbol_name = name if name not in variants else variants[name]
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


def get_imports_from_submodules(input_template: Template, all_runtime_deps: Dict[str, str]):

    def clean_import_name(name):
        return name.replace('\'', '').replace(';', '').replace('"', '').replace('\n', '')

    files = [f for f in glob.glob(str(input_template.path / "src" / "lib") + "**/*.ts", recursive=True)]

    lines = []
    for file in files:
        with open(file, 'r') as fp:
            lines = lines + [line for line in fp.readlines() if 'from \'' in line or 'from "' in line]

    imports_from = [clean_import_name(line.split("from ")[-1]) for line in lines]
    packages_imports_from = {line for line in imports_from if line and line[0] != '.'}
    imports_from_dependencies = {clean_import_name(f): next((dep for dep in all_runtime_deps.keys() if dep in f), None)
                                 for f in packages_imports_from}
    imports_from_sub_modules = {k: {"package": v, "path": k.split(v)[1]}
                                for k, v in imports_from_dependencies.items() if k != v}
    return imports_from_sub_modules


def generate_test_files(working_path: Path):
    f = open(working_path / 'src' / 'tests' / 'fake.test.ts', 'w')
    f.write("// @ts-ignore \ntest('fake test waiting for better', () => expect(true).toBeTruthy())")
    f.close()
