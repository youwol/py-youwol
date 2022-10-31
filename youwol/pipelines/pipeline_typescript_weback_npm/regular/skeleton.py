import functools
import json
import shutil
from base64 import b64encode
from pathlib import Path
from typing import Dict, NamedTuple

from youwol.environment.models_project import ProjectTemplate
from youwol.pipelines.pipeline_typescript_weback_npm import get_externals, DevServer, Bundles, MainModule
from youwol.pipelines.pipeline_typescript_weback_npm.common import Template, generate_package_json, \
    copy_files_folders, generate_webpack_config, PackageType, Dependencies, RunTimeDeps
from youwol.utils.utils_low_level import sed_inplace
from youwol_utils.context import Context
from youwol_utils.http_clients.cdn_backend import get_api_key

#  Expose here for backward compatibility
PackageType = PackageType
Dependencies = Dependencies
RunTimeDeps = RunTimeDeps
Template = Template

auto_generated_filename = 'auto-generated.ts'


class Files(NamedTuple):
    pipeline_folder = '.yw_pipeline'
    pipeline_file = '.yw_pipeline/yw_pipeline.py'
    pipeline_file_template_lib = '.yw_pipeline/yw_pipeline.lib.txt'
    pipeline_file_template_app = '.yw_pipeline/yw_pipeline.app.txt'


def generate_template(input_template: Template):

    working_path = input_template.path / '.template'
    externals, exported_symbols = get_externals(input_template=input_template)

    if working_path.is_dir():
        shutil.rmtree(path=working_path)
    Path(working_path).mkdir()
    base_template_path = Path(__file__).parent / 'templates'
    copy_files_folders(
        working_path=working_path,
        base_template_path=base_template_path,
        files=['.gitignore', '.npmignore', '.prettierignore', 'jest.config.js', 'LICENSE', 'tsconfig.json',
               'typedoc.js'],
        folders=[])

    generate_pipeline(base_template_path=base_template_path, working_path=working_path, input_template=input_template)

    src_target = 'src.app' if input_template.type == PackageType.Application else 'src.lib'

    shutil.copytree(src=base_template_path / src_target,
                    dst=working_path / 'src',
                    )

    shutil.copyfile(src=Path(__file__).parent / 'templates' / auto_generated_filename,
                    dst=working_path / 'src' / auto_generated_filename)

    generate_package_json(source=Path(__file__).parent / 'templates' / 'package.json',
                          working_path=working_path, input_template=input_template)
    generate_autogenerated(working_path=working_path, input_template=input_template, externals=externals,
                           exported_symbols=exported_symbols)
    generate_readme(working_path=working_path, input_template=input_template)
    webpack_config_src = 'webpack.config.lib.ts' \
        if input_template.type == PackageType.Library\
        else 'webpack.config.app.ts'
    generate_webpack_config(source=Path(__file__).parent / 'templates' / webpack_config_src,
                            working_path=working_path,
                            input_template=input_template
                            )
    generate_test_files(working_path=working_path)


def generate_pipeline(base_template_path: Path, working_path: Path, input_template: Template):

    (working_path / Files.pipeline_folder).mkdir()

    if input_template.type == PackageType.Library:
        shutil.copyfile(src=base_template_path / Files.pipeline_file_template_lib,
                        dst=working_path / Files.pipeline_file)
    else:
        shutil.copyfile(src=base_template_path / Files.pipeline_file_template_app,
                        dst=working_path / Files.pipeline_file)
        sed_inplace(working_path / Files.pipeline_file, "{{name}}", input_template.name)


def generate_autogenerated(working_path: Path, input_template: Template, externals, exported_symbols):
    for pattern, repl in [
        ["name", input_template.name],
        ["assetId", b64encode(input_template.name.encode('ascii')).decode('ascii')],
        ["version", input_template.version],
        ["apiVersion", get_api_key(input_template.version)],
        ['shortDescription', input_template.shortDescription],
        ['developerDocumentation',
         f"https://platform.youwol.com/applications/@youwol/cdn-explorer/latest?package={input_template.name}"],
        ['npmPackage', f"https://www.npmjs.com/package/{input_template.name}"],
        ['sourceGithub', f"https://github.com/{input_template.name.replace('@','')}"],
        ['userGuide', f"https://l.youwol.com/doc/{input_template.name}"if input_template.userGuide else ""],
        ['main-entry-file', input_template.bundles.mainModule.entryFile]
    ]:
        sed_inplace(working_path / 'src' / auto_generated_filename, "{{"+pattern+"}}", repl)

    secondary_entries = functools.reduce(
        lambda acc, e: {**acc, e.name: e.dict()},
        input_template.bundles.auxiliaryModules, {}
    )
    for pattern, repl in [
        ["'{{runTimeDependencies}}'", json.dumps(input_template.dependencies.runTime.dict(), indent=4)],
        ["'{{externals}}'", json.dumps(externals, indent=4)],
        ["'{{exportedSymbols}}'", json.dumps(exported_symbols, indent=4)],
        ["'{{mainEntry}}'", json.dumps(input_template.bundles.mainModule.dict(), indent=4)],
        ["'{{secondaryEntries}}'", json.dumps(secondary_entries, indent=4)]
    ]:
        sed_inplace(working_path / 'src' / auto_generated_filename, pattern, repl)


def generate_readme(working_path: Path, input_template: Template):

    filename = working_path / 'README.md'
    base_src_path = Path(__file__).parent / 'templates'
    if input_template.type == PackageType.Library:
        shutil.copyfile(base_src_path / 'README.lib.md', working_path / 'README.md')
    if input_template.type == PackageType.Application:
        shutil.copyfile(base_src_path / 'README.app.md', working_path / 'README.md')

    user_guide = f"[Online user-guide](https://l.youwol.com/doc/{input_template.name})" \
        if input_template.userGuide else ""

    dev_documentation = \
        "[Developers documentation](https://platform.youwol.com/applications/@youwol/cdn-explorer/latest" \
        f"?package={input_template.name})"

    running_app = f"[Running app.](https://platform.youwol.com/applications/{input_template.name}/latest)"

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
        ['runningApp', running_app],
        ['userGuide', user_guide],
        ['testConfig', test_config],
        ['devServer.port', str(input_template.devServer.port) if input_template.devServer else ""]
    ]:
        sed_inplace(filename, "{{"+pattern+"}}", repl)


def generate_test_files(working_path: Path):
    path_dir_tests = working_path / 'src' / 'tests'
    path_dir_tests.mkdir(parents=True)
    f = open(path_dir_tests / 'fake.test.ts', 'w')
    f.write("// @ts-ignore \ntest('fake test waiting for better', () => expect(true).toBeTruthy())")
    f.close()


imTsSrc = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAABGdBTUEAALGPC"\
          "/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAA81BMVEVVVaowd8cxeMYyeMcweMYxeMYxd8YxeMY"\
          "weMYxd8YxeMZCg8tMis5AgsoyecaYvOPW5PSOteBjmdTG2e/4+v3////x9vudv+SxzOqlxOZ7qNr9/f7H2vCQtuDI2/Dr8vnn7/iGsN04"\
          "fcjf6vaPteB6qNrF2e9dldJDhMtZktGDrt3s8/q60uxak9Fyo9j6/P7D2O5Tjs9hmNPX5fT2+f1uoNczecZwodfS4fI5fciev+RBg8pGh"\
          "sxqndZYkdHw9fucvuRhl9O91O39/v9FhcyxzOlIh8zT4vP+/v/y9/s1e8dLic1Ehctgl9NxothqntZVj9BaXTTcAAAACnRSTlMDet97eeH"\
          "e4N148PDkcQAAAAFiS0dEFeXY+aMAAAAHdElNRQflBQwNDQC1Hf1HAAAA6klEQVQ4y2NgYGTiwgmYGBkYmLnwAhYGVvwK2Bi4CIBRBTRXwM"\
          "3Dy4esgF8ADgS5uISERURFRcXEkRRIiMKBJJeUNIQlg6RAVk5OTl5UVAFIKSqJiYoqq6iqqAmjuUECpBsI1IGaeUAMDRwKNIEKtLD5AqZAS"\
          "RuoQkcXtwIuPX2QEw0McSrgMjIGqTAxxamAy8zcAhQQljgVcHHxWQFVqGNXYG0NIm2ACmyxK7CzdxDicXQSFXV2waEAFuiuOBzp5u4BkvZ0"\
          "8AIpYEco8NbVdYOwfHz9/ANA0lwcDIz40wsnAwMnnuzPxskAAFAwOIumrED4AAAAJXRFWHRkYXRlOmNyZWF0ZQAyMDIxLTA1LTEyVDEzOjE"\
          "zOjAwKzAwOjAwL0SI0wAAACV0RVh0ZGF0ZTptb2RpZnkAMjAyMS0wNS0xMlQxMzoxMzowMCswMDowMF4ZMG8AAAAASUVORK5CYII= "


class Keys(NamedTuple):
    name = "name"
    dev_server_port = "dev-server's port"


def lib_ts_webpack_template(folder: Path):

    return ProjectTemplate(
        icon={"tag": 'img', "src": imTsSrc},
        type='ts+webpack library',
        folder=folder,
        parameters={Keys.name: "provide the name of the library here"},
        generator=lambda _folder, params, context:
        generate_ts_webpack_project(folder, params, PackageType.Library, context)
    )


def app_ts_webpack_template(folder: Path):

    return ProjectTemplate(
        icon={"tag": 'img', "src": imTsSrc},
        type='ts+webpack app.',
        folder=folder,
        parameters={Keys.name: "provide the name of the application here", Keys.dev_server_port: "5000"},
        generator=lambda _folder, params, context:
        generate_ts_webpack_project(folder, params, PackageType.Application, context)
    )


async def generate_ts_webpack_project(folder: Path, parameters: Dict[str, str], package_type: PackageType,
                                      context: Context):

    async with context.start("Generate ts webpack project"):

        if Keys.name not in parameters:
            raise RuntimeError(f"Expect 'name' in parameters")
        name = parameters[Keys.name]
        project_folder = folder / name

        if not folder.exists():
            raise RuntimeError(f"Folder {folder} does not exist")

        if project_folder.exists():
            raise RuntimeError(f"Folder {folder} already exist")

        project_folder.mkdir(parents=True)
        load_deps = {
            "@youwol/cdn-client": "^1.0.2",
            "@youwol/flux-view": "^1.0.3",
            "rxjs": "^6.5.5",
        }
        template = Template(
            path=project_folder,
            type=PackageType.Library if package_type == PackageType.Library else PackageType.Application,
            name=name,
            version="0.1.0-wip",
            dependencies=Dependencies(
                runTime=RunTimeDeps(
                    externals=load_deps
                )
            ),
            bundles=Bundles(
                mainModule=MainModule(
                    entryFile='./lib/index.ts',
                    loadDependencies=["@youwol/cdn-client", "@youwol/flux-view", "rxjs"]
                )
            ),
            userGuide=True
        )
        if package_type == PackageType.Application:
            template.devServer = DevServer(port=int(parameters[Keys.dev_server_port]))

        generate_template(template)
        shutil.copytree(
            src=project_folder / '.template',
            dst=project_folder,
            dirs_exist_ok=True
        )
        src_template = Path(__file__).parent / 'templates' / 'template.lib.txt' \
            if package_type == PackageType.Library \
            else Path(__file__).parent / 'templates' / 'template.app.txt'

        shutil.copyfile(
            src=src_template,
            dst=project_folder / 'template.py'
        )
        for pattern, repl in [
            ["loadDependencies", json.dumps(load_deps)],
            ["loadDependenciesName", json.dumps(list(load_deps.keys()))],
            ["devServerPort", parameters[Keys.dev_server_port] if Keys.dev_server_port in parameters else ""]
        ]:
            sed_inplace(project_folder / 'template.py', "{{"+pattern+"}}", repl)
        return name, project_folder
