import os
import shutil
import zipfile
from enum import Enum
from pathlib import Path
from typing import List, Union, Optional, Dict, Callable

from appdirs import AppDirs
from pydantic import BaseModel

from youwol.configuration import Events
from youwol.configuration.python_function_runner import PythonSourceFunction, get_python_function
from youwol.main_args import get_main_arguments
from youwol.middlewares.dynamic_routing.custom_dispatch_rules import AbstractDispatch, RedirectDispatch

default_http_port: int = 2000
default_openid_host: str = "gc.auth.youwol.com"
default_path_config: Path = Path("config.json")


class ConfigPortRange(BaseModel):
    start: int
    end: int


default_port_range: ConfigPortRange = ConfigPortRange(start=3000, end=4000)


class ConfigCdnServer(BaseModel):
    name: str
    port: int


class ConfigCdn(BaseModel):
    auto_update: bool = True
    servers: List[Union[str, ConfigCdnServer]]


class ConfigSource(BaseModel):
    source: Optional[str]
    function: str


class Dispatch(BaseModel):
    origin: str
    destination: str


def ensure_source_file(arg: Union[str, ConfigSource], default_source: str, default_root: str) -> ConfigSource:
    result = arg
    if not isinstance(result, ConfigSource):
        result = ConfigSource(function=arg)

    if not result.source:
        result.source = default_source

    if not Path(result.source).is_absolute():
        result.source = str(Path(default_root) / Path(result.source))

    return result


class ConfigBase(BaseModel):
    httpPort: Optional[int]
    openIdHost: Optional[str]
    user: Optional[str]
    projectsDirs: Optional[Union[str, List[str]]]
    configDir: Optional[str]
    dataDir: Optional[str]
    cacheDir: Optional[str]
    serversPortsRange: Optional[ConfigPortRange]
    cdn: Optional[ConfigCdn]
    source: Optional[str]
    customDispatches: Optional[List[Dispatch]]
    events: Dict[str, Union[str, ConfigSource]] = {}
    customCommands: Dict[str, Union[str, ConfigSource]] = {}
    customize: Optional[Union[str, ConfigSource]] = None


def replace_with(parent: ConfigBase, replacement: ConfigBase) -> ConfigBase:
    return ConfigBase(
        httpPort=replacement.openIdHost if replacement.openIdHost else parent.httpPort,
        openIdHost=replacement.openIdHost if replacement.openIdHost else parent.openIdHost,
        user=replacement.user if replacement.user else parent.user,
        projectsDirs=replacement.projectsDirs if replacement.projectsDirs else parent.projectsDirs,
        configDir=replacement.configDir if replacement.configDir else parent.configDir,
        dataDir=replacement.dataDir if replacement.dataDir else parent.dataDir,
        cacheDir=replacement.cacheDir if replacement.cacheDir else parent.cacheDir,
        serversPortsRange=replacement.serversPortsRange if replacement.serversPortsRange else parent.serversPortsRange,
        cdn=replacement.cdn if replacement.cdn else parent.cdn,
        source=replacement.source if replacement.source else parent.source,
        events=replacement.events if replacement.events else parent.events,
        customCommands=replacement.customCommands if replacement.customCommands else parent.customCommands,
        customDispatches=replacement.customDispatches if replacement.customDispatches else parent.customDispatches,
        customize=replacement.customize if replacement.customize else parent.customize
    )


def append(parent: ConfigBase, appended: ConfigBase) -> ConfigBase:
    pass


class CascadeBaseProfile(Enum):
    REPLACE = "replace"
    APPEND = "append"


class CascadeReplace(BaseModel):
    replaced_profile: str


class CascadeAppend(BaseModel):
    append_to_profile: str


class ConfigProfile(ConfigBase):
    cascade: Union[CascadeAppend, CascadeReplace, CascadeBaseProfile] = CascadeBaseProfile.APPEND


class ConfigWhole(ConfigBase):
    projectsDirs: Optional[Union[str, List[str]]]
    profiles: Optional[Dict[str, ConfigProfile]] = {}
    profile: Optional[str]


class Configuration:
    path: Path
    config_dir: Path
    config_data: ConfigWhole
    effective_config_data: ConfigBase
    active_profile: Optional[str] = None
    app_dirs = AppDirs(appname="py-youwol", appauthor="Youwol")

    def __init__(self, path: Optional[Path] = None, profile: Optional[str] = None):

        path = path if path else default_path_config
        (final_path, exists) = existing_path_or_default(path,
                                                        root_candidates=[Path().cwd(),
                                                                         self.app_dirs.user_config_dir,
                                                                         Path().home()],
                                                        default_root=self.app_dirs.user_config_dir)

        self.path = final_path
        self.config_dir = self.path.parent
        if exists:
            if not final_path.is_file():
                raise PathException(f"'{str(final_path)}' is not a file")
            else:
                self.config_data = ConfigWhole.parse_file(self.path)
        else:
            self.config_data = ConfigWhole.parse_raw("{}")

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

        path = self.effective_config_data.dataDir if self.effective_config_data.dataDir else "databases"
        return ensure_dir_exists(path, root_candidates=self.app_dirs.user_data_dir, create=create_data_dir)

    def get_cache_dir(self) -> Path:
        path = self.effective_config_data.cacheDir if self.effective_config_data.cacheDir else "system"
        return ensure_dir_exists(path, root_candidates=self.app_dirs.user_cache_dir)

    def get_projects_dirs(self) -> List[Path]:
        if not self.effective_config_data.projectsDirs:
            return [ensure_dir_exists("Projects", root_candidates=Path.home())]
        elif isinstance(self.effective_config_data.projectsDirs, str):
            return [ensure_dir_exists(self.effective_config_data.projectsDirs, root_candidates=Path().home())]
        else:
            return [ensure_dir_exists(path_str, root_candidates=Path().home()) for path_str in self.effective_config_data.projectsDirs]

    def get_live_servers(self) -> Dict[str, int]:
        if not self.effective_config_data.cdn:
            return {}

        port_range: ConfigPortRange = self.effective_config_data.serversPortsRange if self.effective_config_data.serversPortsRange else default_port_range

        assigned_ports = [cdnServer.port for cdnServer in self.effective_config_data.cdn.servers if
                          isinstance(cdnServer, ConfigCdnServer)]

        def ensure_port_defined(server_definition: Union[str, ConfigCdnServer]) -> ConfigCdnServer:
            if isinstance(server_definition, ConfigCdnServer):
                return server_definition

            port = port_range.start
            while port in assigned_ports:
                port = port + 1

            assigned_ports.append(port)
            return ConfigCdnServer(name=server_definition, port=port)

        return {server.name: server.port for server in
                [ensure_port_defined(name_or_object) for name_or_object in self.effective_config_data.cdn.servers]}

    def get_events(self) -> Events:
        result = {}

        for (key, conf) in self.effective_config_data.events.items():
            conf = ensure_source_file(conf, self.effective_config_data.source, self.app_dirs.user_config_dir)
            result[key] = PythonSourceFunction(path=Path(conf.source), name=conf.function)

        return Events(onLoad=get_python_function(result["on_load"]) if "on_load" in result else None)

    def get_cdn_auto_update(self) -> bool:
        if self.effective_config_data.cdn:
            if self.effective_config_data.cdn.auto_update:
                return self.effective_config_data.cdn.auto_update

        return True

    def get_commands(self) -> Dict[str, PythonSourceFunction]:
        result = {}

        for (key, conf) in self.effective_config_data.customCommands:
            conf = ensure_source_file(conf, self.effective_config_data.source, self.app_dirs.user_config_dir)
            result[key] = PythonSourceFunction(path=Path(conf.source), name=conf.function)

        return result

    def customize(self, youwol_configuration):
        if not self.effective_config_data.customize:
            return youwol_configuration

        conf = ensure_source_file(self.effective_config_data.customize, self.effective_config_data.source,
                                  self.app_dirs.user_config_dir)
        return get_python_function(PythonSourceFunction(path=Path(conf.source),
                                                        name=conf.function))(youwol_configuration)

    def get_custom_dispatches(self) -> List[AbstractDispatch]:
        if not self.effective_config_data.customDispatches:
            return []

        return [RedirectDispatch(origin=dispatch.origin, destination=dispatch.destination) for dispatch in
                self.effective_config_data.customDispatches]


class PathException(RuntimeError):
    path: str


def default_create_dir(final_path: Path):
    try:
        final_path.mkdir(parents=True)
    except Exception as e:
        raise PathException(f"Error while creating '{str(final_path)}' : {e}")


def ensure_dir_exists(path: Optional[Union[str, Path]],
                      root_candidates: Union[Union[str, Path], List[Union[str, Path]]],
                      default_root: Optional[Union[str, Path]] = None,
                      create: Optional[Callable[[Path], None]] = default_create_dir) -> Path:
    path = path if path else "."
    (final_path, exists) = existing_path_or_default(path, root_candidates=root_candidates, default_root=default_root)

    if exists:
        if not final_path.is_dir():
            raise PathException(f"'{str(final_path)}' is not a directory")
    else:
        create(final_path)

    return final_path


def ensure_file_exists(path: Union[str, Path],
                       root_candidates: Union[Union[str, Path], List[Union[str, Path]]],
                       default_root: Optional[Union[str, Path]] = None,
                       default_content: Optional[str] = None) -> Path:
    (final_path, exists) = existing_path_or_default(path, root_candidates=root_candidates, default_root=default_root)

    if exists:
        if not final_path.is_file():
            raise PathException(f"'{str(final_path)}' is not a file")
    else:
        if default_content:
            try:
                final_path.parent.mkdir(parents=True, exist_ok=True)
                final_path.write_text(default_content)
            except Exception as e:
                raise PathException(f"Error while creating '{str(final_path)}' : {e}")
        else:
            raise PathException(f"'{str(final_path)}' does not exist")

    return final_path


def existing_path_or_default(path: Union[str, Path],
                             root_candidates: Union[Union[str, Path], List[Union[str, Path]]],
                             default_root: Optional[Union[str, Path]] = None) -> (Path, bool):
    typed_path = Path(path)

    if typed_path.is_absolute():
        return typed_path, typed_path.exists()

    if not isinstance(root_candidates, List):
        root_candidates = [root_candidates]

    root_candidates_idx = 0
    while root_candidates_idx < len(root_candidates):
        absolute_path = Path(root_candidates[root_candidates_idx]) / typed_path
        if absolute_path.exists():
            return absolute_path, True
        root_candidates_idx = root_candidates_idx + 1

    final_root = Path(default_root) if default_root else Path(root_candidates[0])
    return final_root / typed_path, False
