import importlib
import os
import shutil
import sys
import traceback
import zipfile
from abc import ABC, abstractmethod
from enum import Enum
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path
from typing import List, Union, Optional, Dict, Awaitable, cast, TypeVar, Type, Callable, Any

from pydantic import BaseModel

from youwol.configuration.models_dispatch import CdnOverrideDispatch, AbstractDispatch, RedirectDispatch
from youwol.configuration.models_project import format_unknown_error, ErrorResponse, Pipeline
from youwol.configuration.configuration_validation import ConfigurationLoadingException, \
    CheckValidConfigurationFunction, ConfigurationLoadingStatus
from youwol.configuration.defaults import default_path_projects_dir, default_path_data_dir, \
    default_path_cache_dir, default_http_port, default_openid_host, default_port_range_start, default_port_range_end
from youwol.configuration.util_paths import ensure_dir_exists, existing_path_or_default, fail_on_missing_dir, \
    PathException, app_dirs
from youwol.configurations import YouwolEnvironment
from youwol.context import Context
from youwol.main_args import get_main_arguments, MainArguments
from youwol.routers.custom_commands.models import Command


class Events(BaseModel):
    onLoad: Callable[[YouwolEnvironment, Context], Optional[Union[Any, Awaitable[Any]]]] = None


class ConfigPortRange(BaseModel):
    start: int
    end: int


ConfigPath = Union[str, Path]


class ConfigModuleLoading(BaseModel):
    path: Optional[ConfigPath]
    name: str

    def __str__(self):
        return f"{self.path}#{self.name}"


class ConfigurationProfile(BaseModel):
    httpPort: Optional[int]
    openIdHost: Optional[str]
    user: Optional[str]
    projectsDirs: Optional[Union[ConfigPath, List[ConfigPath]]]
    configDir: Optional[ConfigPath]
    dataDir: Optional[ConfigPath]
    cacheDir: Optional[ConfigPath]
    serversPortsRange: Optional[ConfigPortRange]
    cdnAutoUpdate: Optional[bool]
    dispatches: Optional[List[Union[str, RedirectDispatch, CdnOverrideDispatch, AbstractDispatch]]]
    defaultModulePath: Optional[ConfigPath]
    events: Optional[Union[Events, str, ConfigModuleLoading]]
    customCommands: List[Union[str, Command, ConfigModuleLoading]] = []
    customize: Optional[Union[str, ConfigModuleLoading]]


def replace_with(parent: ConfigurationProfile, replacement: ConfigurationProfile) -> ConfigurationProfile:
    return ConfigurationProfile(
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


class CascadeBaseProfile(Enum):
    REPLACE = "replace"
    APPEND = "append"


class CascadeReplace(BaseModel):
    replaced_profile: str


class CascadeAppend(BaseModel):
    append_to_profile: str


class ConfigurationProfileCascading(ConfigurationProfile):
    cascade: Union[CascadeAppend, CascadeReplace, CascadeBaseProfile] = CascadeBaseProfile.APPEND


class Configuration(ConfigurationProfile):
    profiles: Optional[Dict[str, ConfigurationProfileCascading]] = {}
    profile: Optional[str]


class IConfigurationFactory(ABC):

    @abstractmethod
    async def get(self, _main_args: MainArguments) -> Configuration:
        return NotImplemented


class IPipelineFactory(ABC):

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    async def get(self) -> Pipeline:
        return NotImplemented


class IConfigurationCustomizer(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def customize(self, _youwol_configuration: YouwolEnvironment) -> YouwolEnvironment:
        return NotImplemented


class ConfigurationHandler:
    path: Path
    config_data: Configuration
    effective_config_data: ConfigurationProfile
    active_profile: Optional[str] = None

    def __init__(self, path: Path, config_data: Configuration, profile: Optional[str]):
        self.path = path
        self.config_data = config_data
        if profile:
            self.set_profile(profile)
        else:
            self.set_profile(self.config_data.profile)

    def get_openid_host(self) -> str:
        return self.effective_config_data.openIdHost if self.effective_config_data.openIdHost else default_openid_host

    def set_profile(self, profile: str):
        if profile in self.config_data.profiles.keys():
            config = self.config_data.profiles.get(profile)
            self.effective_config_data = replace_with(self.config_data, config)
            self.active_profile = profile
        else:
            self.effective_config_data = self.config_data

    def get_profile(self) -> str:
        return self.active_profile if self.active_profile else "default"

    def get_available_profiles(self) -> List[str]:
        return ["default", *list(self.config_data.profiles.keys())]

    def get_http_port(self) -> int:
        return self.effective_config_data.httpPort if self.effective_config_data.httpPort else default_http_port

    def get_config_dir(self) -> Path:
        path = self.effective_config_data.configDir if self.effective_config_data.configDir else self.path.parent
        return ensure_dir_exists(path, root_candidates=app_dirs.user_config_dir)

    def get_data_dir(self) -> Path:
        def create_data_dir(final_path: Path):
            final_path.parent.mkdir(parents=True)
            shutil.copyfile(get_main_arguments().youwol_path.parent / 'youwol_data' / 'databases.zip',
                            final_path.parent / 'databases.zip')

            with zipfile.ZipFile(final_path.parent / 'databases.zip', 'r') as zip_ref:
                zip_ref.extractall(final_path.parent)

            os.remove(final_path.parent / 'databases.zip')

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

        port_range: ConfigPortRange = self.effective_config_data.serversPortsRange \
            if self.effective_config_data.serversPortsRange else ConfigPortRange(start=default_port_range_start,
                                                                                 end=default_port_range_end)

        assigned_ports = [cdnServer.port for cdnServer in self.effective_config_data.dispatches
                          if isinstance(cdnServer, CdnOverrideDispatch)]

        def get_abstract_dispatch(
                dispatch: Union[str, AbstractDispatch]) -> AbstractDispatch:

            if isinstance(dispatch, CdnOverrideDispatch):
                return CdnOverrideDispatch(packageName=dispatch.packageName, port=dispatch.port)

            if isinstance(dispatch, RedirectDispatch):
                return RedirectDispatch(origin=dispatch.origin, destination=dispatch.destination)

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

        if isinstance(self.effective_config_data.events, str):
            config_loading = ConfigModuleLoading(name=self.effective_config_data.events)
        else:
            config_loading = self.effective_config_data.events

        config_loading = ensure_loading_source_exists(config_loading, self.effective_config_data.defaultModulePath)

        return get_object_from_module(module_absolute_path=config_loading.path,
                                      object_or_class_name=config_loading.name,
                                      object_type=Events)

    def get_cdn_auto_update(self) -> bool:
        if not self.effective_config_data.cdnAutoUpdate:
            return True

        return self.effective_config_data.cdnAutoUpdate

    def get_commands(self) -> Dict[str, Command]:
        def get_command(arg: Union[str, ConfigModuleLoading, Command]) -> (str, Command):
            conf_loading = arg
            if isinstance(arg, Command):
                return conf_loading.name, conf_loading
            if isinstance(arg, str):
                conf_loading = ConfigModuleLoading(name=arg)

            conf_loading = ensure_loading_source_exists(conf_loading, self.effective_config_data.defaultModulePath)
            command = get_object_from_module(conf_loading.path, conf_loading.name, Command)
            return command.name, command

        return {name: command for (name, command) in [get_command(conf) for conf in
                                                      self.effective_config_data.customCommands]}

    def customize(self, youwol_configuration):
        if not self.effective_config_data.customize:
            return youwol_configuration

        config_source = ensure_loading_source_exists(self.effective_config_data.customize,
                                                     self.effective_config_data.defaultModulePath)

        customizer = get_object_from_module(module_absolute_path=config_source.path,
                                            object_or_class_name=config_source.name,
                                            object_type=IConfigurationCustomizer)
        try:
            youwol_configuration = customizer.customize(youwol_configuration)
        except Exception as e:
            raise Exception(f"Error while executing customizer {config_source}.customize(…) : {e}")

        return youwol_configuration


def ensure_loading_source_exists(arg: Union[str, ConfigModuleLoading],
                                 default_source: ConfigPath) -> ConfigModuleLoading:
    result = arg
    default_root = app_dirs.user_config_dir
    if not isinstance(result, ConfigModuleLoading):
        result = ConfigModuleLoading(name=arg)

    if not result.path:
        result.path = Path(default_source)

    if not Path(result.path).is_absolute():
        result.path = Path(default_root) / Path(result.path)

    if not result.path.exists():
        raise PathException(f"{str(result.path)} does not exists")

    if not result.path.is_file():
        raise PathException(f"'{str(result.path)}' is not a file")
    return result


async def configuration_from_json(path: Path, profile: Optional[str]) -> ConfigurationHandler:
    (final_path, exists) = existing_path_or_default(path,
                                                    root_candidates=[Path().cwd(),
                                                                     app_dirs.user_config_dir,
                                                                     Path().home()],
                                                    default_root=app_dirs.user_config_dir)

    if not exists:
        raise PathException(f"{str(final_path)} does not exists")

    if not final_path.is_file():
        raise PathException(f"'{str(final_path)}' is not a file")

    config_data = Configuration.parse_file(final_path)

    return ConfigurationHandler(path=final_path, config_data=config_data, profile=profile)


async def configuration_from_python(path: Path, profile: Optional[str]) -> ConfigurationHandler:
    (final_path, exists) = existing_path_or_default(path,
                                                    root_candidates=[Path().cwd(),
                                                                     app_dirs.user_config_dir,
                                                                     Path().home()],
                                                    default_root=app_dirs.user_config_dir)

    if not exists:
        raise PathException(f"{str(final_path)} does not exists")

    if not final_path.is_file():
        raise PathException(f"'{str(final_path)}' is not a file")

    check_valid_conf_fct = CheckValidConfigurationFunction()

    def get_status(validated: bool = False):
        return ConfigurationLoadingStatus(
            path=str(path),
            validated=validated,
            checks=[
                check_valid_conf_fct,
            ]
        )

    factory = get_object_from_module(module_absolute_path=final_path, object_or_class_name="ConfigurationFactory",
                                     object_type=IConfigurationFactory)
    try:
        result = factory.get(get_main_arguments())
        config_data: Configuration = await result if isinstance(result, Awaitable) else result
    except Exception as err:
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)
        check_valid_conf_fct.status = format_unknown_error(
            reason=f"There was an exception calling the 'configuration'.",
            error=err)
        raise ConfigurationLoadingException(get_status(False))

    if not isinstance(config_data, Configuration):
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"The function 'configuration' must return an instance of type 'Configuration'",
            hints=[f"You can have a look at the default_config_yw.py located in 'py-youwol/system'"])
        raise ConfigurationLoadingException(get_status(False))

    return ConfigurationHandler(path=final_path, config_data=config_data, profile=profile)


T = TypeVar('T')


def get_object_from_module(
        module_absolute_path: Path,
        object_or_class_name: str,
        object_type: Type[T],
        **object_instantiation_kwargs
) -> T:
    def get_instance_from_module(imported_module):
        if not hasattr(imported_module, object_or_class_name):
            raise Exception(f"{module_absolute_path} : Expected class '{object_or_class_name}' not found")

        maybe_class_or_var = imported_module.__getattribute__(object_or_class_name)

        if isinstance(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var)

        if issubclass(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var(**object_instantiation_kwargs))

        raise Exception(f"{module_absolute_path} : Expected class '{object_or_class_name}'"
                        f" does not implements expected type '{object_type}")

    module_name = module_absolute_path.stem
    try:
        loader = SourceFileLoader(module_name, str(module_absolute_path))
        spec = spec_from_loader(module_name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        instance = get_instance_from_module(module)
    except SyntaxError as e:
        raise Exception(f"{module_absolute_path} : Syntax error '{e}'")
    except NameError as e:
        raise Exception(f"{module_absolute_path} :Name error '{e}")

    return instance
