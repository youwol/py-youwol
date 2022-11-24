import inspect
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Callable, cast, Optional, Set, Dict

from youwol import environment
from youwol.configuration.defaults import default_platform_host
from youwol.configuration.models_config import Configuration, Events, ConfigPath, RemoteConfig
from youwol.configuration.models_config_middleware import CustomMiddleware
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models import IConfigurationCustomizer, Projects
from youwol.environment.paths import app_dirs
from youwol.environment.utils import default_projects_finder
from youwol.main_args import get_main_arguments
from youwol.routers.custom_commands.models import Command
from youwol_utils import Context
from youwol_utils.servers.fast_api import FastApiRouter
from youwol_utils.utils_paths import ensure_dir_exists

SKELETON_DATABASES_ARCHIVE = 'databases.zip'


def append_with(_parent, _appended):
    raise NotImplementedError("Appending not yet implemented")


class ConfigurationHandler:
    path: Path
    config_data: Configuration

    def __init__(self, path: Path, config_data: Configuration):
        self.path = path
        self.config_data = config_data

    def get_http_port(self) -> int:
        return self.config_data.system.httpPort

    def get_config_dir(self) -> Path:
        path = self.config_data.system.configDir if self.config_data.system.configDir else self.path.parent
        return ensure_dir_exists(path, root_candidates=app_dirs.user_config_dir)

    def get_data_dir(self) -> Path:
        def create_data_dir(final_path: Path):
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(get_main_arguments().youwol_path.parent / 'youwol_data' / SKELETON_DATABASES_ARCHIVE,
                            final_path.parent / SKELETON_DATABASES_ARCHIVE)

            with zipfile.ZipFile(final_path.parent / SKELETON_DATABASES_ARCHIVE, 'r') as zip_ref:
                zip_ref.extractall(final_path.parent)

            os.remove(final_path.parent / SKELETON_DATABASES_ARCHIVE)

        path = self.config_data.system.dataDir
        return ensure_dir_exists(path, root_candidates=app_dirs.user_data_dir, create=create_data_dir)

    def get_cache_dir(self) -> Path:
        return ensure_dir_exists(self.config_data.system.cacheDir, root_candidates=app_dirs.user_cache_dir)

    def get_projects(self) -> Projects:
        if self.config_data.projects is None:
            return Projects()

        projects = self.config_data.projects
        finder = None
        if callable(projects.finder):
            # finder is Callable[[YouwolEnvironment, Context], List[ConfigPath]]
            # or Callable[[YouwolEnvironment, Context], Awaitable[List[ConfigPath]]]
            is_coroutine = inspect.iscoroutinefunction(projects.finder)

            async def await_finder(env, ctx):
                #  if no cast => python complains about typing w/ ModuleLoading accepting only keyword arguments
                return cast(Callable[[YouwolEnvironment, Context], List[ConfigPath]], projects.finder)(env, ctx)

            finder = projects.finder if is_coroutine else await_finder
        elif isinstance(projects.finder, str) \
                or isinstance(projects.finder, Path) \
                or isinstance(projects.finder, List):
            # finder is List[ConfigPath]
            async def default_finder(env, _ctx):
                return default_projects_finder(env=env, root_folders=projects.finder)

            finder = default_finder

        return environment.models.Projects(
            finder=finder,
            templates=projects.templates,
            uploadTargets=projects.uploadTargets
        )

    def get_middlewares(self) -> List[CustomMiddleware]:
        return self.config_data.customization.middlewares

    def get_events(self) -> Events:
        return self.config_data.customization.events

    def get_commands(self) -> Dict[str, Command]:
        return {c.name: c for c in self.config_data.customization.endPoints.commands}

    def get_routers(self) -> List[FastApiRouter]:
        return self.config_data.customization.endPoints.routers

    def get_remotes(self) -> Set[RemoteConfig]:
        if not self.config_data.system.remotes:
            return {self.get_selected_remote()}
        else:
            return set(self.config_data.system.remotes + [self.get_selected_remote()])

    def get_selected_remote(self) -> Optional[RemoteConfig]:
        selected = self.config_data.system.selectedRemote
        remotes = self.config_data.system.remotes
        if selected is None:
            if len(remotes) > 0:
                return remotes[0]
            else:
                return RemoteConfig.build(default_platform_host)

        if isinstance(selected, str):
            candidates = [remote for remote in remotes if remote.host == selected]
            if len(candidates) > 0:
                return candidates[0]
            else:
                return RemoteConfig.build(selected)

        return selected
