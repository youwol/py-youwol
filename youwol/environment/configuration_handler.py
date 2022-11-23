import inspect
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Union, Dict, Callable, cast, Optional, Set

from youwol import environment
from youwol.configuration.defaults import default_http_port, default_path_data_dir, \
    default_path_cache_dir, default_port_range_start, default_port_range_end, \
    default_platform_host
from youwol.configuration.models_config import Configuration, PortRange, ModuleLoading, \
    CdnOverride, Redirection, Events, ConfigPath, RemoteConfig
from youwol.configuration.models_config_middleware import CustomMiddleware
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.models import IConfigurationCustomizer, Projects
from youwol.environment.paths import app_dirs
from youwol.environment.utils import default_projects_finder
from youwol.main_args import get_main_arguments
from youwol.middlewares.models_dispatch import CdnOverrideDispatch, RedirectDispatch, AbstractDispatch
from youwol.routers.custom_commands.models import Command
from youwol.utils.utils_low_level import get_object_from_module
from youwol_utils import Context
from youwol_utils.servers.fast_api import FastApiRouter
from youwol_utils.utils_paths import PathException, ensure_dir_exists

SKELETON_DATABASES_ARCHIVE = 'databases.zip'


def append_with(_parent, _appended):
    raise NotImplementedError("Appending not yet implemented")


class ConfigurationHandler:
    path: Path
    config_data: Configuration

    def __init__(self, path: Path, config_data: Configuration):
        self.path = path
        self.config_data = config_data

    def get_redirect_base_path(self) -> str:
        return self.config_data.redirectBasePath if self.config_data.redirectBasePath \
            else f"https://{self.get_selected_remote().host}/api"

    def get_http_port(self) -> int:
        return self.config_data.httpPort if self.config_data.httpPort else default_http_port

    def get_config_dir(self) -> Path:
        path = self.config_data.configDir if self.config_data.configDir else self.path.parent
        return ensure_dir_exists(path, root_candidates=app_dirs.user_config_dir)

    def get_data_dir(self) -> Path:
        def create_data_dir(final_path: Path):
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(get_main_arguments().youwol_path.parent / 'youwol_data' / SKELETON_DATABASES_ARCHIVE,
                            final_path.parent / SKELETON_DATABASES_ARCHIVE)

            with zipfile.ZipFile(final_path.parent / SKELETON_DATABASES_ARCHIVE, 'r') as zip_ref:
                zip_ref.extractall(final_path.parent)

            os.remove(final_path.parent / SKELETON_DATABASES_ARCHIVE)

        path = self.config_data.dataDir if self.config_data.dataDir else default_path_data_dir
        return ensure_dir_exists(path, root_candidates=app_dirs.user_data_dir, create=create_data_dir)

    def get_cache_dir(self) -> Path:
        path = self.config_data.cacheDir if self.config_data.cacheDir else default_path_cache_dir
        return ensure_dir_exists(path, root_candidates=app_dirs.user_cache_dir)

    def get_projects(self) -> Projects:
        if self.config_data.projects is None:
            return Projects()

        projects = self.config_data.projects
        finder = None

        if isinstance(projects.finder, ModuleLoading):
            # finder is ModuleLoading
            config_loading = ensure_loading_source_exists(self.config_data.events,
                                                          self.get_default_module_path(),
                                                          self.get_data_dir())

            finder = get_object_from_module(module_absolute_path=config_loading.path,
                                            object_or_class_name=config_loading.name,
                                            object_type=Callable,
                                            additional_src_absolute_paths=self.get_additional_python_src_paths())

        elif callable(projects.finder):
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
        return self.config_data.middlewares or []

    def get_dispatches(self) -> List[AbstractDispatch]:
        if not self.config_data.dispatches:
            return []

        port_range: PortRange = self.config_data.serversPortsRange \
            if self.config_data.serversPortsRange else PortRange(start=default_port_range_start,
                                                                 end=default_port_range_end)

        assigned_ports = [cdnServer.port for cdnServer in self.config_data.dispatches
                          if isinstance(cdnServer, CdnOverrideDispatch)]

        def get_abstract_dispatch(
                dispatch: Union[str, AbstractDispatch]) -> AbstractDispatch:

            if isinstance(dispatch, CdnOverride):
                if dispatch.port is None:
                    dispatch = dispatch.packageName
                else:
                    return CdnOverrideDispatch(packageName=dispatch.packageName, port=dispatch.port)

            if isinstance(dispatch, Redirection):
                return RedirectDispatch(origin=dispatch.from_url_path, destination=dispatch.to_url)

            if isinstance(dispatch, AbstractDispatch):
                return dispatch

            port = port_range.start
            while port in assigned_ports:
                port = port + 1

            assigned_ports.append(port)
            return CdnOverrideDispatch(packageName=dispatch, port=port)

        return [get_abstract_dispatch(dispatch=dispatch) for dispatch in self.config_data.dispatches]

    def get_events(self) -> Events:

        if self.config_data.events is None:
            return Events()

        if isinstance(self.config_data.events, Events):
            return self.config_data.events

        config_loading = ensure_loading_source_exists(self.config_data.events,
                                                      self.get_default_module_path(),
                                                      self.get_data_dir())

        return get_object_from_module(module_absolute_path=config_loading.path,
                                      object_or_class_name=config_loading.name,
                                      object_type=Events,
                                      additional_src_absolute_paths=self.get_additional_python_src_paths())

    def get_default_module_path(self) -> Path:
        if self.config_data.defaultModulePath is None:
            return Path("py-youwol.py")

        return Path(self.config_data.defaultModulePath)

    def get_cdn_auto_update(self) -> bool:
        if not self.config_data.cdnAutoUpdate:
            return True

        return self.config_data.cdnAutoUpdate

    def get_commands(self) -> Dict[str, Command]:
        def get_command(arg: Union[str, ModuleLoading, Command]) -> (str, Command):
            conf_loading = arg
            if isinstance(arg, Command):
                return conf_loading.name, conf_loading

            conf_loading = ensure_loading_source_exists(conf_loading,
                                                        self.get_default_module_path(),
                                                        self.get_data_dir())
            command = get_object_from_module(module_absolute_path=conf_loading.path,
                                             object_or_class_name=conf_loading.name,
                                             object_type=Command,
                                             additional_src_absolute_paths=self.get_additional_python_src_paths())
            return command.name, command

        return {name: command for (name, command) in [get_command(conf) for conf in
                                                      self.config_data.customCommands]}

    async def customize(self, youwol_configuration):
        if not self.config_data.customize:
            return youwol_configuration

        config_source = ensure_loading_source_exists(self.config_data.customize,
                                                     self.get_default_module_path(),
                                                     self.get_data_dir())

        customizer = get_object_from_module(module_absolute_path=config_source.path,
                                            object_or_class_name=config_source.name,
                                            object_type=IConfigurationCustomizer,
                                            additional_src_absolute_paths=self.get_additional_python_src_paths())
        try:
            youwol_configuration = await customizer.customize(youwol_configuration)
        except Exception as e:
            raise RuntimeError(f"Error while executing customizer {config_source}.customize(…) : {e}")

        return youwol_configuration

    def get_additional_python_src_paths(self) -> List[Path]:
        path_user_lib = Path(app_dirs.user_data_dir) / "lib"
        conf_paths = self.config_data.additionalPythonSrcPath
        if not conf_paths:
            return [path_user_lib]

        paths = conf_paths if isinstance(conf_paths, List) else [conf_paths]

        return [ensure_dir_exists(path=path, root_candidates=path_user_lib)
                for path in paths]

    def get_ports_book(self) -> Dict[str, int]:
        return self.config_data.portsBook or {}

    def get_routers(self) -> List[FastApiRouter]:
        return self.config_data.routers or []

    def get_remotes(self) -> Set[RemoteConfig]:
        if not self.config_data.remotes:
            return {self.get_selected_remote()}
        else:
            return set(self.config_data.remotes + [self.get_selected_remote()])

    def get_selected_remote(self) -> Optional[RemoteConfig]:
        selected = self.config_data.selectedRemote

        if selected is None:
            if len(self.config_data.remotes) > 0:
                return self.config_data.remotes[0]
            else:
                return RemoteConfig.build(default_platform_host)

        if isinstance(selected, str):
            candidates = [remote for remote in self.config_data.remotes if remote.host == selected]
            if len(candidates) > 0:
                return candidates[0]
            else:
                return RemoteConfig.build(selected)

        return selected


def ensure_loading_source_exists(arg: Union[str, ModuleLoading],
                                 default_source: Path,
                                 default_root: Path) -> ModuleLoading:
    result = arg
    if not isinstance(result, ModuleLoading):
        result = ModuleLoading(name=arg)

    if not result.path:
        result.path = default_source
    else:
        result.path = Path(result.path)

    if not result.path.is_absolute():
        result.path = default_root / result.path

    if not result.path.exists():
        raise PathException(f"{str(result.path)} does not exists")

    if not result.path.is_file():
        raise PathException(f"'{str(result.path)}' is not a file")

    return result
