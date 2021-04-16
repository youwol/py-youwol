from pathlib import Path
from typing import NamedTuple, Union, Dict
import youwol


class PathsBook(NamedTuple):

    config_path: Path
    system_path: Path
    data_path: Path
    usersInfo: Path
    secret_path: Union[Path, None]
    pinnedPaths: Dict[str, Path] = {}
    youwol: Path = Path(youwol.__file__).parent

    @property
    def local_docdb(self) -> Path:
        return self.data_path / 'docdb'

    @property
    def local_storage(self) -> Path:
        return self.data_path / 'storage'

    @property
    def js_modules_store_path(self) -> Path:
        return self.system_path / "node_modules"

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

    def node_module_dependency(self, target_folder: Union[Path, str], dependency_name: str) -> Path:
        if '/' in dependency_name:
            namespace, name = dependency_name.split('/')
            return self.node_modules(target_folder) / namespace / name

        return self.node_modules(target_folder) / dependency_name
