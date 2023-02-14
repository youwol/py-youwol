from pathlib import Path
from typing import Union, Optional

from appdirs import AppDirs
from pydantic import BaseModel

from youwol_utils.utils_paths import existing_path_or_default

docdb_filename = "data.json"


class PathsBook(BaseModel):

    config: Path
    system: Path
    databases: Path

    @property
    def local_storage(self) -> Path:
        return self.databases / 'storage'

    @property
    def local_cdn_storage(self) -> Path:
        return self.local_storage / 'cdn' / 'youwol-users'

    @property
    def local_stories_storage(self) -> Path:
        return self.local_storage / 'stories' / 'youwol-users'

    @property
    def js_modules_store_path(self) -> Path:
        return self.system / "node_modules"

    def cdn_zip_path(self, name: str, version: str) -> Path:
        return self.store_node_module(name) / (version+'.zip')

    @property
    def packages_cache_filename(self) -> str:
        return "packages-cache.json"

    @property
    def packages_cache_path(self) -> Path:
        return self.js_modules_store_path / self.packages_cache_filename

    @property
    def store_node_modules(self) -> Path:
        return self.js_modules_store_path

    def store_node_module(self, target_name: str) -> Path:
        if '/' in target_name:
            namespace, name = target_name.split('/')
            return self.store_node_modules / namespace / name

        return self.store_node_modules / target_name

    @staticmethod
    def node_modules(target_folder: Union[Path, str]) -> Path:
        return Path(target_folder) / "node_modules"

    @staticmethod
    def node_module_dependency(self, target_folder: Union[Path, str], dependency_name: str) -> Path:
        if '/' in dependency_name:
            namespace, name = dependency_name.split('/')
            return self.node_modules(target_folder) / namespace / name

        return self.node_modules(target_folder) / dependency_name

    def artifacts_flow(self, project_name: str, flow_id: str) -> Path:
        return self.system / project_name / flow_id

    def artifacts_step(self, project_name: str, flow_id: str, step_id: str) -> Path:
        return self.artifacts_flow(project_name=project_name, flow_id=flow_id) / step_id

    def artifact(self, project_name: str, flow_id: str, step_id: str, artifact_id: str) -> Path:
        return self.artifacts_step(project_name=project_name, flow_id=flow_id, step_id=step_id) \
               / f"artifact-{artifact_id}"

    def artifacts_manifest(self, project_name: str, flow_id: str, step_id: str):
        return self.artifacts_step(project_name=project_name, flow_id=flow_id, step_id=step_id) / 'manifest.json'

    def __str__(self):
        return f"""
 * config file: {self.config}
 * databases directory: {self.databases}
 * system directory: {self.system}
"""


app_dirs = AppDirs(appname="py-youwol", appauthor="Youwol")


def ensure_config_file_exists_or_create_it(path: Optional[Path]) -> (Path, bool):
    path = path if path else Path("config.py")
    (final_path, exists) = existing_path_or_default(path,
                                                    root_candidates=[Path().cwd(),
                                                                     app_dirs.user_config_dir,
                                                                     Path().home()],
                                                    default_root=app_dirs.user_config_dir)
    if not exists:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text("""
from youwol.environment import Configuration

Configuration()
""")
    return final_path, exists
