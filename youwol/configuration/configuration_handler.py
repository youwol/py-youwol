import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional, List, Union, Dict

from youwol.configuration.defaults import default_openid_host, default_http_port, default_path_data_dir, \
    default_path_cache_dir, default_path_projects_dir, default_port_range_start, default_port_range_end
from youwol.configuration.models_config import Profiles, ConfigurationData, PortRange, ModuleLoading, \
    CascadeBaseProfile, CascadeAppend, CascadeReplace, CdnOverride, Redirection
from youwol.environment.models import Events, IConfigurationCustomizer
from youwol.environment.paths import app_dirs
from youwol.main_args import get_main_arguments
from youwol.middlewares.models_dispatch import CdnOverrideDispatch, RedirectDispatch, AbstractDispatch
from youwol.routers.custom_commands.models import Command
from youwol.utils_low_level import get_object_from_module
from youwol_utils.utils_paths import PathException, fail_on_missing_dir, ensure_dir_exists

SKELETON_DATABASES_ARCHIVE = 'databases.zip'


def append_with(_parent, _appended):
    raise NotImplementedError("Appending not yet implemented")


def replace_with(parent: ConfigurationData, replacement: ConfigurationData) -> ConfigurationData:
    return ConfigurationData(
        httpPort=replacement.openIdHost if replacement.openIdHost else parent.httpPort,
        openIdHost=replacement.openIdHost if replacement.openIdHost else parent.openIdHost,
        user=replacement.user if replacement.user else parent.user,
        projectsDirs=replacement.projectsDirs if replacement.projectsDirs else parent.projectsDirs,
        configDir=replacement.configDir if replacement.configDir else parent.configDir,
        dataDir=replacement.dataDir if replacement.dataDir else parent.dataDir,
        cacheDir=replacement.cacheDir if replacement.cacheDir else parent.cacheDir,
        serversPortsRange=replacement.serversPortsRange if replacement.serversPortsRange else parent.serversPortsRange,
        cdnAutoUpdate=replacement.cdnAutoUpdate if replacement.cdnAutoUpdate else parent.cdnAutoUpdate,
        dispatches=replacement.dispatches if replacement.dispatches else parent.dispatches,
        defaultModulePath=replacement.defaultModulePath if replacement.defaultModulePath else parent.defaultModulePath,
        events=replacement.events if replacement.events else parent.events,
        customCommands=replacement.customCommands if replacement.customCommands else parent.customCommands,
        customize=replacement.customize if replacement.customize else parent.customize,
    )


class ConfigurationHandler:
    path: Path
    config_data: Profiles
    effective_config_data: ConfigurationData
    active_profile: Optional[str] = None

    def __init__(self, path: Path, config_data: Profiles, profile: Optional[str]):
        self.path = path
        self.config_data = config_data
        if profile:
            self.set_profile(profile)
        else:
            self.set_profile(self.config_data.selected)

    def get_openid_host(self) -> str:
        return self.effective_config_data.openIdHost if self.effective_config_data.openIdHost else default_openid_host

    def set_profile(self, profile: str):
        if profile in self.config_data.extending_profiles.keys():
            config_cascading = self.config_data.extending_profiles.get(profile)
            if config_cascading.cascade == CascadeBaseProfile.REPLACE:
                self.effective_config_data = replace_with(self.config_data.default, config_cascading.config_data)
            elif config_cascading.cascade == CascadeBaseProfile.APPEND:
                self.effective_config_data = append_with(self.config_data.default, config_cascading.config_data)
            elif isinstance(config_cascading.cascade, CascadeReplace):
                parent = self.config_data.extending_profiles.get(config_cascading.cascade.replaced_profile).config_data
                self.effective_config_data = replace_with(parent, config_cascading.config_data)
            elif isinstance(config_cascading.cascade, CascadeAppend):
                parent = self.config_data.extending_profiles.get(config_cascading.cascade.append_to_profile).config_data
                self.effective_config_data = append_with(parent, config_cascading.config_data)
            self.active_profile = profile
        else:
            self.effective_config_data = self.config_data.default

    def get_profile(self) -> str:
        return self.active_profile if self.active_profile else "default"

    def get_available_profiles(self) -> List[str]:
        return ["default", *list(self.config_data.extending_profiles.keys())]

    def get_http_port(self) -> int:
        return self.effective_config_data.httpPort if self.effective_config_data.httpPort else default_http_port

    def get_config_dir(self) -> Path:
        path = self.effective_config_data.configDir if self.effective_config_data.configDir else self.path.parent
        return ensure_dir_exists(path, root_candidates=app_dirs.user_config_dir)

    def get_data_dir(self) -> Path:
        def create_data_dir(final_path: Path):
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(get_main_arguments().youwol_path.parent / 'youwol_data' / SKELETON_DATABASES_ARCHIVE,
                            final_path.parent / SKELETON_DATABASES_ARCHIVE)

            with zipfile.ZipFile(final_path.parent / SKELETON_DATABASES_ARCHIVE, 'r') as zip_ref:
                zip_ref.extractall(final_path.parent)

            os.remove(final_path.parent / SKELETON_DATABASES_ARCHIVE)

        path = self.effective_config_data.dataDir if self.effective_config_data.dataDir else default_path_data_dir
        return ensure_dir_exists(path, root_candidates=app_dirs.user_data_dir, create=create_data_dir)

    def get_cache_dir(self) -> Path:
        path = self.effective_config_data.cacheDir if self.effective_config_data.cacheDir else default_path_cache_dir
        return ensure_dir_exists(path, root_candidates=app_dirs.user_cache_dir)

    def get_projects_dirs(self) -> List[Path]:
        path = self.effective_config_data.projectsDirs \
            if self.effective_config_data.projectsDirs else default_path_projects_dir
        if isinstance(path, str) or isinstance(path, Path):
            return [ensure_dir_exists(path, root_candidates=Path().home(), create=fail_on_missing_dir)]
        else:
            return [ensure_dir_exists(path_str, root_candidates=Path().home(), create=fail_on_missing_dir)
                    for path_str in self.effective_config_data.projectsDirs]

    def get_dispatches(self) -> List[AbstractDispatch]:
        if not self.effective_config_data.dispatches:
            return []

        port_range: PortRange = self.effective_config_data.serversPortsRange \
            if self.effective_config_data.serversPortsRange else PortRange(start=default_port_range_start,
                                                                           end=default_port_range_end)

        assigned_ports = [cdnServer.port for cdnServer in self.effective_config_data.dispatches
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

        return [get_abstract_dispatch(dispatch=dispatch) for dispatch in self.effective_config_data.dispatches]

    def get_events(self) -> Events:

        if self.effective_config_data.events is None:
            return Events()

        if isinstance(self.effective_config_data.events, Events):
            return self.effective_config_data.events

        config_loading = ensure_loading_source_exists(self.effective_config_data.events,
                                                      self.get_default_module_path(),
                                                      self.get_data_dir())

        return get_object_from_module(module_absolute_path=config_loading.path,
                                      object_or_class_name=config_loading.name,
                                      object_type=Events,
                                      additional_src_absolute_paths=self.get_additional_python_src_paths())

    def get_default_module_path(self) -> Path:
        if self.effective_config_data.defaultModulePath is None:
            return Path("py-youwol.py")

        return Path(self.effective_config_data.defaultModulePath)

    def get_cdn_auto_update(self) -> bool:
        if not self.effective_config_data.cdnAutoUpdate:
            return True

        return self.effective_config_data.cdnAutoUpdate

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
                                                      self.effective_config_data.customCommands]}

    def customize(self, youwol_configuration):
        if not self.effective_config_data.customize:
            return youwol_configuration

        config_source = ensure_loading_source_exists(self.effective_config_data.customize,
                                                     self.get_default_module_path(),
                                                     self.get_data_dir())

        customizer = get_object_from_module(module_absolute_path=config_source.path,
                                            object_or_class_name=config_source.name,
                                            object_type=IConfigurationCustomizer,
                                            additional_src_absolute_paths=self.get_additional_python_src_paths())
        try:
            youwol_configuration = customizer.customize(youwol_configuration)
        except Exception as e:
            raise Exception(f"Error while executing customizer {config_source}.customize(…) : {e}")

        return youwol_configuration

    def get_additional_python_src_paths(self) -> List[Path]:
        path_user_lib = Path(app_dirs.user_data_dir) / "lib"
        conf_paths = self.effective_config_data.additionalPythonSrcPath
        if not conf_paths:
            return [path_user_lib]

        paths = conf_paths if isinstance(conf_paths, List) else [conf_paths]

        return [ensure_dir_exists(path=path, root_candidates=path_user_lib)
                for path in paths]


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
