import shutil
from pathlib import Path

from youwol.pipelines.pipeline_typescript_weback_npm.common import Template, generate_package_json, \
    copy_files_folders, generate_webpack_config, PackageType, Dependencies, RunTimeDeps
from youwol.utils.utils_low_level import sed_inplace

#  Expose here for backward compatibility
PackageType = PackageType
Dependencies = Dependencies
RunTimeDeps = RunTimeDeps
Template = Template


def generate_template(input_template: Template):

    working_path = input_template.path / '.template'
    if working_path.is_dir():
        shutil.rmtree(path=working_path)
    Path(working_path).mkdir()
    copy_files_folders(
        working_path=working_path,
        base_template_path=Path(__file__).parent / 'templates',
        files=['.gitignore', '.npmignore', '.prettierignore', 'jest.config.js', 'LICENSE', 'tsconfig.json',
               'typedoc.js'],
        folders=['.yw_pipeline', 'src'])
    generate_package_json(source=Path(__file__).parent / 'templates' / 'package.json',
                          working_path=working_path, input_template=input_template)
    generate_readme(working_path=working_path, input_template=input_template)
    generate_webpack_config(source=Path(__file__).parent / 'templates' / 'webpack.config.lib.js',
                            working_path=working_path,
                            input_template=input_template)
    generate_test_files(working_path=working_path)


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


def generate_test_files(working_path: Path):
    f = open(working_path / 'src' / 'tests' / 'fake.test.ts', 'w')
    f.write("// @ts-ignore \ntest('fake test waiting for better', () => expect(true).toBeTruthy())")
    f.close()
