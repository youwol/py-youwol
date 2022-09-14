import json
import shutil
from base64 import b64encode
from pathlib import Path

from youwol.pipelines.pipeline_typescript_weback_npm import get_externals
from youwol.pipelines.pipeline_typescript_weback_npm.common import Template, generate_package_json, \
    copy_files_folders, generate_webpack_config, PackageType, Dependencies, RunTimeDeps
from youwol.utils.utils_low_level import sed_inplace
from youwol_utils import parse_json
from youwol_utils.http_clients.cdn_backend import get_api_key

#  Expose here for backward compatibility
PackageType = PackageType
Dependencies = Dependencies
RunTimeDeps = RunTimeDeps
Template = Template

auto_generated_filename = 'auto-generated.ts'


def generate_template(input_template: Template):

    working_path = input_template.path / '.template'
    package_json = parse_json(input_template.path / 'package.json')
    externals, exported_symbols = get_externals(input_template=input_template)

    if not input_template.name:
        input_template.name = package_json['name']
    if not input_template.version:
        input_template.version = package_json['version']
    if not input_template.shortDescription:
        input_template.shortDescription = package_json.get('description', "")
    if not input_template.author:
        input_template.shortDescription = package_json.get('author', "")

    if working_path.is_dir():
        shutil.rmtree(path=working_path)
    Path(working_path).mkdir()
    base_template_path = Path(__file__).parent / 'templates'
    copy_files_folders(
        working_path=working_path,
        base_template_path=base_template_path,
        files=['.gitignore', '.npmignore', '.prettierignore', 'jest.config.js', 'LICENSE', 'tsconfig.json',
               'typedoc.js'],
        folders=['.yw_pipeline'])

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
    ]:
        sed_inplace(working_path / 'src' / auto_generated_filename, "{{"+pattern+"}}", repl)

    for pattern, repl in [
        ["'{{runTimeDependencies}}'", json.dumps(input_template.dependencies.runTime.dict(), indent=4)],
        ["'{{externals}}'", json.dumps(externals, indent=4)],
        ["'{{exportedSymbols}}'", json.dumps(exported_symbols, indent=4)]
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
    f = open(working_path / 'src' / 'tests' / 'fake.test.ts', 'w')
    f.write("// @ts-ignore \ntest('fake test waiting for better', () => expect(true).toBeTruthy())")
    f.close()
