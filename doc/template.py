# standard library
import json
import shutil
import tomllib

from collections.abc import Iterable
from pathlib import Path

# Youwol utilities
from youwol.utils import AnyDict, parse_json, write_json, yw_doc_version

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm import (
    Bundles,
    Dependencies,
    DevServer,
    MainModule,
    PackageType,
    RunTimeDeps,
    Template,
)
from youwol.pipelines.pipeline_typescript_weback_npm.regular import generate_template

folder_path = Path(__file__).parent

pkg_json = parse_json(folder_path / "package.json")

externals_deps = {
    "@youwol/mkdocs-ts": "^0.1.1",
    "@youwol/rx-vdom": "^1.0.1",
    "@youwol/webpm-client": "^3.0.0",
    "rxjs": "^7.5.6",
    "@youwol/local-youwol-client": "^0.2.1",
    "@youwol/rx-tab-views": "^0.3.0",
}

in_bundle_deps = {}
dev_deps = {}

template = Template(
    path=folder_path,
    type=PackageType.APPLICATION,
    name=pkg_json["name"],
    version=pkg_json["version"],
    shortDescription=pkg_json["description"],
    author=pkg_json["author"],
    dependencies=Dependencies(
        runTime=RunTimeDeps(externals=externals_deps, includedInBundle=in_bundle_deps),
        devTime=dev_deps,
    ),
    bundles=Bundles(
        mainModule=MainModule(
            entryFile="./main.ts", loadDependencies=list(externals_deps.keys())
        ),
    ),
    userGuide=True,
    devServer=DevServer(port=3021),
)

generate_template(template)
shutil.copyfile(
    src=folder_path / ".template" / "src" / "auto-generated.ts",
    dst=folder_path / "src" / "auto-generated.ts",
)
for file in [
    "README.md",
    ".npmignore",
    ".prettierignore",
    "LICENSE",
    "package.json",
    "tsconfig.json",
    "webpack.config.ts",
]:
    shutil.copyfile(src=folder_path / ".template" / file, dst=folder_path / file)

"""
Below is the generation of the file `src/auto-generated-toml`
"""
py_yw_folder = Path(__file__).parent / ".."


def format_pythons(project: AnyDict) -> str:
    keyword = "Programming Language :: Python :: "
    versions = [d.split(keyword)[1] for d in project["classifiers"] if keyword in d]
    return format_list([v for v in versions if v != "3"])


def format_list(items: Iterable[str]) -> str:
    quoted_items = [f"'{item}'" for item in items]
    return f"[{', '.join(quoted_items)}],"


def make_autogenerated_toml():
    dest_file = py_yw_folder / "doc" / "src" / "auto-generated-toml.ts"
    with open(py_yw_folder / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
        ts = f"""export const youwolInfo = {{
    version: '{data['project']['version']}',
    pythons: {format_pythons(data['project'])}
}}
"""
        with open(dest_file, "w", encoding="UTF-8") as fp:
            fp.write(ts)

        pkg_json_path = py_yw_folder / "doc" / "package.json"
        package_json = parse_json(pkg_json_path)

        package_json["version"] = yw_doc_version()
        with open(pkg_json_path, "w", encoding="UTF-8") as fp:
            json.dump(package_json, fp, indent=4)
            fp.write("\n")


make_autogenerated_toml()

"""
Below is copying the `CHANGELOG.md` in the assets folder.
"""

shutil.copyfile(
    src=py_yw_folder / "CHANGELOG.md", dst=folder_path / "assets" / "CHANGELOG.md"
)
