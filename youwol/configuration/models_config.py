import importlib
import os
import shutil
import sys
import traceback
import zipfile
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Union, Optional, Dict, Callable, Any, Awaitable, cast, TypeVar, Type

from pydantic import BaseModel

from youwol.configuration.models_project import format_unknown_error, ErrorResponse, Pipeline
from youwol.configuration.configuration_validation import ConfigurationLoadingException, \
    CheckValidConfigurationFunction, ConfigurationLoadingStatus
from youwol.configuration.defaults import default_path_projects_dir, default_path_data_dir, \
    default_path_cache_dir, default_http_port, default_openid_host
from youwol.configuration.python_function_runner import PythonSourceFunction, get_python_function
from youwol.configuration.util_paths import ensure_dir_exists, existing_path_or_default, fail_on_missing_dir, \
    PathException, app_dirs
from youwol.main_args import get_main_arguments, MainArguments
from youwol.middlewares.dynamic_routing.custom_dispatch_rules import AbstractDispatch, RedirectDispatch, \
    CdnOverrideDispatch


Context = 'youwol.context.Context'
YouwolConfiguration = 'youwol.configuration.YouwolConfiguration'


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    memberOf: List[str]


class RemoteGateway(BaseModel):
    name: str
    host: str
    metadata: Dict[str, str]


class Secret(BaseModel):
    clientId: str
    clientSecret: str


class ConfigPortRange(BaseModel):
    start: int
    end: int


default_port_range: ConfigPortRange = ConfigPortRange(start=3000, end=4000)


ConfigPath = Union[str, Path]


class ConfigSource(BaseModel):
    source: Optional[ConfigPath]
    function: str

    def __str__(self):
        return f"{self.source}#{self.function}"


class Events(BaseModel):
    onLoad: Callable[[YouwolConfiguration, Context], Optional[Union[Any, Awaitable[Any]]]] = None


class EventsImplicit(BaseModel):
    onLoad: Union[ConfigSource, str]


class Redirection(BaseModel):
    origin: str
    destination: str


class CdnOverride(BaseModel):
    name: str
    port: int


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
    dispatches: Optional[List[Union[str, Redirection, CdnOverride]]]
    source: Optional[ConfigPath]
    events: Optional[Union[Events, EventsImplicit]]
    customCommands: Dict[str, Union[str, ConfigSource]] = {}
    customize: Optional[Union[str, ConfigSource]]


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
        source=replacement.source if replacement.source else parent.source,
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


class ConfigurationHandler:
    path: Path
    config_data: Configuration
    effective_config_data: ConfigurationProfile
    active_profile: Optional[str] = None

    def __init__(self, path: Path, config_data: Configuration,  profile: Optional[str]):
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
            if self.effective_config_data.serversPortsRange else default_port_range

        assigned_ports = [cdnServer.port for cdnServer
                          in self.effective_config_data.dispatches if isinstance(cdnServer, CdnOverride)]

        def get_abstract_dispatch(
                dispatch: Union[str, CdnOverride, Redirection]) -> AbstractDispatch:
            if isinstance(dispatch, CdnOverride):
                return CdnOverrideDispatch(package_name=dispatch.name, port=dispatch.port)

            if isinstance(dispatch, Redirection):
                return RedirectDispatch(origin=dispatch.origin, destination=dispatch.destination)

            port = port_range.start
            while port in assigned_ports:
                port = port + 1

            assigned_ports.append(port)
            return CdnOverrideDispatch(package_name=dispatch, port=port)

        return [get_abstract_dispatch(dispatch=dispatch) for dispatch in self.effective_config_data.dispatches]

    def get_events(self) -> Events:

        if self.effective_config_data.events is None:
            return Events()

        if isinstance(self.effective_config_data.events, Events):
            return self.effective_config_data.events

        events: EventsImplicit = self.effective_config_data.events
        python_src = get_python_src(events.onLoad, self.effective_config_data.source)

        return Events(onLoad=get_python_function(python_src))

    def get_cdn_auto_update(self) -> bool:
        if not self.effective_config_data.cdnAutoUpdate:
            return True

        return self.effective_config_data.cdnAutoUpdate

    def get_commands(self) -> Dict[str, PythonSourceFunction]:
        return {key: get_python_src(conf, self.effective_config_data.source)
                for (key, conf) in self.effective_config_data.customCommands}

    def customize(self, youwol_configuration):
        if not self.effective_config_data.customize:
            return youwol_configuration

        python_src = get_python_src(self.effective_config_data.customize, self.effective_config_data.source)

        try:
            youwol_configuration = get_python_function(python_src)(youwol_configuration)
        except Exception as e:
            raise Exception(f"Error while executing customize function {python_src.path}#{python_src.name}", e)

        return youwol_configuration


def get_python_src(arg: Union[str, ConfigSource], default_source: Path) -> PythonSourceFunction:
    result = arg
    default_root = app_dirs.user_config_dir
    if not isinstance(result, ConfigSource):
        result = ConfigSource(function=arg)

    if not result.source:
        result.source = default_source

    if not Path(result.source).is_absolute():
        result.source = str(Path(default_root) / Path(result.source))

    return PythonSourceFunction(path=result.source, name=result.function)


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

    python_paths = sys.path
    if str(final_path.parent) not in python_paths:
        python_paths.append(str(path.parent))

    check_valid_conf_fct = CheckValidConfigurationFunction()

    def get_status(validated: bool = False):
        return ConfigurationLoadingStatus(
            path=str(path),
            validated=validated,
            checks=[
                check_valid_conf_fct,
            ]
        )

    def format_syntax_error(syntax_error: Union[SyntaxError, NameError]):
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"Syntax error detected in the configuration file ({syntax_error.filename})\n" +
                   f"Error location: line {e.lineno}, near '{syntax_error.text.strip()}'",
            hints=[syntax_error.msg])

    main_args = get_main_arguments()
    try:
        module_config = importlib.import_module(final_path.stem)
    except SyntaxError as e:
        format_syntax_error(syntax_error=e)
        raise ConfigurationLoadingException(get_status(False))
    except NameError as e:
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"Name error detected in the configuration file.\n",
            hints=[str(e)])

        raise ConfigurationLoadingException(get_status(False))

    if not hasattr(module_config, 'ConfigurationFactory'):
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"The python configuration file does not contain the definition"
                   "'class ConfigurationFactory(IConfigurationFactory)'",
            hints=[f"Define on in your python's configuration file."])
        raise ConfigurationLoadingException(get_status(False))

    maybe_factory = module_config.__getattribute__("ConfigurationFactory")

    if not issubclass(maybe_factory, IConfigurationFactory):
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"The ConfigurationFactory must implement 'IConfigurationFactory'",
            hints=[f""])
        raise ConfigurationLoadingException(get_status(False))

    factory = cast(IConfigurationFactory, maybe_factory())
    try:
        result = factory.get(main_args)
        config_data: Configuration = await result if isinstance(result, Awaitable) else result
    except SyntaxError as e:
        format_syntax_error(syntax_error=e)
        raise ConfigurationLoadingException(get_status(False))
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


def load_class_from_module(
        python_file_path: Path,
        expected_class_name: str,
        expected_base_class: Type[T],
        **kwargs
        ) -> T:

    # check that filename does not contain invalid character for modules (e.g. '-' ,...)
    python_paths = sys.path
    if str(python_file_path.parent) not in python_paths:
        python_paths.append(str(python_file_path.parent))

    module_name = python_file_path.stem
    try:
        module = importlib.import_module(module_name)
        if str(python_file_path.parent) in python_paths:
            sys.path = [p for p in python_paths if p != str(python_file_path.parent)]

    except SyntaxError:
        raise Exception(f"{python_file_path} : Syntax error")
    except NameError:
        raise Exception(f"{python_file_path} :Name error")

    if not hasattr(module, expected_class_name):
        raise Exception(f"{python_file_path} : Expected class '{expected_class_name}' not found")

    maybe_factory = module.__getattribute__(expected_class_name)

    if not issubclass(maybe_factory, expected_base_class):
        raise Exception(f"{python_file_path} : Expected class '{expected_class_name}' does not implements expected "
                        f"interface")

    factory = cast(expected_base_class, maybe_factory(**kwargs))
    del sys.modules[module_name]
    return factory
