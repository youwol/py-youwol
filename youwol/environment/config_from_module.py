from __future__ import annotations

import sys
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Awaitable

from youwol.configuration.configuration_validation import CheckValidConfigurationFunction, ConfigurationLoadingStatus, \
    ConfigurationLoadingException
from youwol.configuration.models_config import Configuration
from youwol.environment.configuration_handler import ConfigurationHandler
from youwol.environment.models_project import format_unknown_error, ErrorResponse
from youwol.environment.paths import app_dirs
from youwol.main_args import MainArguments, get_main_arguments
from youwol.utils.utils_low_level import get_object_from_module
from youwol_utils.utils_paths import PathException, existing_path_or_default


class IConfigurationFactory(ABC):

    @abstractmethod
    async def get(self, _main_args: MainArguments) -> Configuration:
        return NotImplemented


async def configuration_from_python(path: Path) -> ConfigurationHandler:
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

    factory = get_object_from_module(module_absolute_path=final_path,
                                     object_or_class_name="ConfigurationFactory",
                                     object_type=IConfigurationFactory,
                                     additional_src_absolute_paths=[final_path.parent,
                                                                    Path(app_dirs.user_data_dir) / "lib"]
                                     )
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
            reason=f"The function 'IConfigurationFactory#get()' must return an instance of type 'ConfigurationData'",
            hints=[f"You can have a look at the default_config_yw.py located in 'py-youwol/system'"])
        raise ConfigurationLoadingException(get_status(False))

    return ConfigurationHandler(path=final_path,
                                config_data=config_data)
