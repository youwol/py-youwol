from __future__ import annotations

import sys
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Awaitable, Dict, Union

from youwol.configuration.configuration_handler import ConfigurationHandler
from youwol.configuration.configuration_validation import CheckValidConfigurationFunction, ConfigurationLoadingStatus, \
    ConfigurationLoadingException
from youwol.configuration.models_config import Profiles, ConfigurationData, \
    CascadeAppend, CascadeReplace, CascadeBaseProfile, ConfigurationProfileCascading
from youwol.utils_low_level import get_object_from_module
from youwol.configuration.models_project import format_unknown_error, ErrorResponse
from youwol.utils_paths import app_dirs, PathException, existing_path_or_default
from youwol.main_args import MainArguments, get_main_arguments


class IConfigurationFactory(ABC):

    @abstractmethod
    async def get(self, _main_args: MainArguments) -> Configuration:
        return NotImplemented


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
        config_data = await result if isinstance(result, Awaitable) else result
    except Exception as err:
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)
        check_valid_conf_fct.status = format_unknown_error(
            reason=f"There was an exception calling 'IConfigurationFactory#get()'.",
            error=err)
        raise ConfigurationLoadingException(get_status(False))

    if not isinstance(config_data, Configuration):
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"The function 'IConfigurationFactory#get()' must return an instance of type 'Configuration'",
            hints=[f"You can have a look at the default_config_yw.py located in 'py-youwol/system'"])
        raise ConfigurationLoadingException(get_status(False))

    return ConfigurationHandler(path=final_path,
                                config_data=Profiles(default=config_data,
                                                     others=config_data.get_others(),
                                                     selected=config_data.get_profile()),
                                profile=profile)


class Configuration(ConfigurationData):
    _profiles: Dict[str, Configuration] = {}
    _selected: str = 'default'
    _cascading: Optional[Union[CascadeAppend, CascadeReplace, CascadeBaseProfile]] = None

    def other(self,
              name: str,
              conf: Configuration,
              cascading: Union[CascadeAppend, CascadeReplace, CascadeBaseProfile]
              = CascadeBaseProfile.REPLACE) -> Configuration:
        if self._cascading is not None:
            raise Exception("Configuration#other(…) on anything but base profile is forbidden")
        if name in self._profiles:
            raise Exception(f"There is already a profile named '{name}'")
        conf._cascading = cascading
        self._profiles[name] = conf
        return self

    def get_cascading(self):
        return self._cascading

    def get_others(self) -> Dict[str, ConfigurationProfileCascading]:
        return {key: (ConfigurationProfileCascading(config_data=conf, cascade=conf.get_cascading()))
                for (key, conf) in self._profiles.items()}

    def profile(self, name: str) -> Configuration:
        self._selected = name
        return self

    def get_profile(self):
        return self._selected

    class Config:
        underscore_attrs_are_private = True
