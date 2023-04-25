# standard library
import shutil

from pathlib import Path

# Youwol backends
from youwol.backends.cdn import get_api_key

# Youwol utilities
from youwol.utils.utils_paths import sed_inplace

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm.common import (
    Dependencies,
    RunTimeDeps,
    Template,
    copy_files_folders,
    generate_package_json,
    generate_webpack_config,
)


def generate_template(input_template: Template):
    working_path = input_template.path / ".template"
    if working_path.is_dir():
        shutil.rmtree(path=working_path)

    input_template.dependencies = Dependencies(
        runTime=RunTimeDeps(
            externals={},
            includedInBundle={
                **input_template.dependencies.runTime.includedInBundle,
                input_template.name: input_template.version,
            },
        ),
        devTime=input_template.dependencies.devTime,
    )
    Path(working_path).mkdir()
    copy_files_folders(
        working_path=working_path,
        base_template_path=Path(__file__).parent / "templates",
        files=[".gitignore", "tsconfig.json"],
        folders=[".yw_pipeline", "src"],
    )
    fill_src_files(working_path=working_path, input_template=input_template)
    generate_package_json(
        source=Path(__file__).parent / "templates" / "package.json",
        working_path=working_path,
        input_template=input_template,
    )
    generate_readme(working_path=working_path, input_template=input_template)
    generate_webpack_config(
        source=Path(__file__).parent / "templates" / "webpack.config.lib.js",
        working_path=working_path,
        input_template=input_template,
    )


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


def fill_src_files(working_path: Path, input_template: Template):
    filename = working_path / "src" / "index.ts"
    api_version = get_api_key(input_template.version)
    for pattern, repl in [
        ["name", input_template.name],
        ["exportedSymbol", input_template.exportedSymbol or input_template.name],
        ["apiVersion", api_version],
    ]:
        sed_inplace(filename, "{{" + pattern + "}}", repl)
