import os
import shutil
import sys
import traceback
import zipfile
from enum import Enum
from pathlib import Path
from typing import List, Union, Optional, Dict

from pydantic import BaseModel

from youwol.configuration import Events, ErrorResponse, format_unknown_error
from youwol.configuration.configuration_validation import ConfigurationLoadingException, \
    CheckValidConfigurationFunction, ConfigurationLoadingStatus
from youwol.configuration.defaults import default_path_projects_dir, default_path_data_dir, \
    default_path_cache_dir, default_http_port, default_openid_host
from youwol.configuration.python_function_runner import PythonSourceFunction, get_python_function
from youwol.configuration.util_paths import ensure_dir_exists, existing_path_or_default, fail_on_missing_dir, \
    PathException, app_dirs
from youwol.main_args import get_main_arguments
from youwol.middlewares.dynamic_routing.custom_dispatch_rules import AbstractDispatch, RedirectDispatch, AssetDispatch


class ConfigPortRange(BaseModel):
    start: int
    end: int


default_port_range: ConfigPortRange = ConfigPortRange(start=3000, end=4000)


class ConfigAssetDispatch(BaseModel):
    name: str
    port: int


class ConfigSource(BaseModel):
    source: Optional[str]
    function: str


class ConfigRedirectionDispatch(BaseModel):
    origin: str
    destination: str


class ConfigurationProfile(BaseModel):
    httpPort: Optional[int]
    openIdHost: Optional[str]
    user: Optional[str]
    projectsDirs: Optional[Union[str, List[str]]]
    configDir: Optional[str]
    dataDir: Optional[str]
    cacheDir: Optional[str]
    serversPortsRange: Optional[ConfigPortRange]
    cdnAutoUpdate: Optional[bool]
    dispatches: Optional[List[Union[str, ConfigRedirectionDispatch, ConfigAssetDispatch]]]
    source: Optional[str]
    events: Dict[str, Union[str, ConfigSource]] = {}
    customCommands: Dict[str, Union[str, ConfigSource]] = {}
    customize: Optional[Union[str, ConfigSource]] = None


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


def append(parent: ConfigurationProfile, appended: ConfigurationProfile) -> ConfigurationProfile:
    pass


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


class ConfigurationHandler:
    path: Path
    config_dir: Path
    config_data: Configuration
    effective_config_data: ConfigurationProfile
    active_profile: Optional[str] = None

    def __init__(self, path: Path, config_data: Configuration,  profile: Optional[str]):
        self.path = path
        self.config_data = config_data
        self.config_dir = self.path.parent
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
                          in self.effective_config_data.dispatches if isinstance(cdnServer, ConfigAssetDispatch)]

        def get_abstract_dispatch(
                dispatch: Union[str, ConfigAssetDispatch, ConfigRedirectionDispatch]) -> AbstractDispatch:
            if isinstance(dispatch, ConfigAssetDispatch):
                return AssetDispatch(package_name=dispatch.name, port=dispatch.port)

            if isinstance(dispatch, ConfigRedirectionDispatch):
                return RedirectDispatch(origin=dispatch.origin, destination=dispatch.destination)

            port = port_range.start
            while port in assigned_ports:
                port = port + 1

            assigned_ports.append(port)
            return AssetDispatch(package_name=dispatch, port=port)

        return [get_abstract_dispatch(dispatch=dispatch) for dispatch in self.effective_config_data.dispatches]

    def get_events(self) -> Events:
        result = {}

        for (key, conf) in self.effective_config_data.events.items():
            conf = ensure_source_file(conf, self.effective_config_data.source, app_dirs.user_config_dir)
            result[key] = PythonSourceFunction(path=Path(conf.source), name=conf.function)

        return Events(onLoad=get_python_function(result["on_load"]) if "on_load" in result else None)

    def get_cdn_auto_update(self) -> bool:
        if not self.effective_config_data.cdnAutoUpdate:
            return True

        return self.effective_config_data.cdnAutoUpdate

    def get_commands(self) -> Dict[str, PythonSourceFunction]:
        result = {}

        for (key, conf) in self.effective_config_data.customCommands:
            conf = ensure_source_file(conf, self.effective_config_data.source, app_dirs.user_config_dir)
            result[key] = PythonSourceFunction(path=Path(conf.source), name=conf.function)

        return result

    def customize(self, youwol_configuration):
        if not self.effective_config_data.customize:
            return youwol_configuration

        conf = ensure_source_file(self.effective_config_data.customize, self.effective_config_data.source,
                                  app_dirs.user_config_dir)
        return get_python_function(PythonSourceFunction(path=Path(conf.source),
                                                        name=conf.function))(youwol_configuration)


def ensure_source_file(arg: Union[str, ConfigSource], default_source: str, default_root: str) -> ConfigSource:
    result = arg
    if not isinstance(result, ConfigSource):
        result = ConfigSource(function=arg)

    if not result.source:
        result.source = default_source

    if not Path(result.source).is_absolute():
        result.source = str(Path(default_root) / Path(result.source))

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

    try:
        main_args = get_main_arguments()
        config_data: Configuration = await get_python_function(
            PythonSourceFunction(path=path, name='configuration'))(main_args, profile)
        if not isinstance(config_data, Configuration):
            check_valid_conf_fct.status = ErrorResponse(
                reason=f"The function 'configuration' must return an instance of type 'UserConfiguration'",
                hints=[f"You can have a look at the default_config_yw.py located in 'py-youwol/system'"])
            raise ConfigurationLoadingException(get_status(False))
    # except ValidationError as err:
    #     check_valid_conf_fct.status = ErrorResponse(
    #         reason=f"Parsing the object returned by the function 'async def configuration(...)' " +
    #                "to UserConfiguration failed.",
    #         hints=[f"{str(err)}"])
    #     raise ConfigurationLoadingException(get_status(False))
    # except TypeError as err:
    #     ex_type, ex, tb = sys.exc_info()
    #     traceback.print_tb(tb)
    #     check_valid_conf_fct.status = ErrorResponse(
    #         reason=f"Misused of configuration function",
    #         hints=[f"details: {str(err)}"])
    #     raise ConfigurationLoadingException(get_status(False))
    except Exception as err:
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)
        check_valid_conf_fct.status = format_unknown_error(
            reason=f"There was an exception calling the 'configuration'.",
            error=err)
        raise ConfigurationLoadingException(get_status(False))

    return ConfigurationHandler(path=final_path, config_data=config_data, profile=profile)
