from typing import NamedTuple

from youwol.routers.projects.models_project import Project
from youwol_utils import parse_json


class Paths(NamedTuple):
    package_json_file = "package.json"
    lib_folder = "src/lib"
    auto_generated_file = "**/auto_generated.ts"


def get_dependencies(project: Project):
    package_json = parse_json(project.path / Paths.package_json_file)
    return set({
                   **package_json.get("dependencies", {}),
                   **package_json.get("peerDependencies", {}),
                   **package_json.get("devDependencies", {})
               }.keys())
