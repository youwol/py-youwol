from enum import Enum
from pathlib import Path
from typing import List, Union, Optional, Dict

from pydantic import BaseModel

from youwol.configuration.models_k8s import K8sCluster
from youwol.environment.models import Events
from youwol.middlewares.models_dispatch import AbstractDispatch, RedirectDispatch
from youwol.routers.custom_commands.models import Command
from youwol_utils.servers.fast_api import FastApiRouter


class PortRange(BaseModel):
    start: int
    end: int


ConfigPath = Union[str, Path]


class ModuleLoading(BaseModel):
    path: Optional[ConfigPath]
    name: str

    def __str__(self):
        return f"{self.path}#{self.name}"


class CdnOverride(BaseModel):
    packageName: str
    port: Optional[int]


class Redirection(BaseModel):
    from_url_path: str
    to_url: str


class ConfigurationData(BaseModel):
    httpPort: Optional[int]
    openIdHost: Optional[str]
    user: Optional[str]
    portsBook: Optional[Dict[str, int]]
    routers: Optional[List[FastApiRouter]]
    projectsDirs: Optional[Union[ConfigPath, List[ConfigPath]]]
    configDir: Optional[ConfigPath]
    dataDir: Optional[ConfigPath]
    cacheDir: Optional[ConfigPath]
    serversPortsRange: Optional[PortRange]
    cdnAutoUpdate: Optional[bool]
    dispatches: Optional[List[Union[str, Redirection, CdnOverride, AbstractDispatch, RedirectDispatch]]]
    defaultModulePath: Optional[ConfigPath]
    additionalPythonSrcPath: Optional[Union[ConfigPath, List[ConfigPath]]]
    events: Optional[Union[Events, str, ModuleLoading]]
    customCommands: List[Union[str, Command, ModuleLoading]] = []
    customize: Optional[Union[str, ModuleLoading]]
    k8sCluster: Optional[K8sCluster]


class CascadeBaseProfile(Enum):
    REPLACE = "replace"
    APPEND = "append"


class CascadeReplace(BaseModel):
    replaced_profile: str


class CascadeAppend(BaseModel):
    append_to_profile: str


Cascade = Union[CascadeAppend, CascadeReplace, CascadeBaseProfile]


class ExtendingProfile(BaseModel):
    config_data: ConfigurationData
    cascade: Cascade = CascadeBaseProfile.REPLACE


class Profiles(BaseModel):
    default: ConfigurationData
    extending_profiles: Dict[str, ExtendingProfile] = {}
    selected: Optional[str]
