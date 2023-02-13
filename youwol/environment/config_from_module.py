from __future__ import annotations

import ast
import importlib
import sys
import traceback
from _ast import mod
from abc import ABC, abstractmethod
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path
from typing import Awaitable, Optional, cast

from youwol.environment.paths import app_dirs
from youwol.environment.errors_handling import CheckValidConfigurationFunction, ConfigurationLoadingStatus, \
    ConfigurationLoadingException, format_unknown_error, ErrorResponse
from youwol.environment.models import Configuration
from youwol.main_args import MainArguments, get_main_arguments
from youwol.environment.python_dynamic_loader import get_object_from_module
from youwol_utils.utils_paths import PathException, existing_path_or_default


class IConfigurationFactory(ABC):

    @abstractmethod
    async def get(self, _main_args: MainArguments) -> Configuration:
        return NotImplemented


def try_last_expression_as_config(config_path: Path) -> Optional[Configuration]:
    """

    :param config_path: path of the config file
    :return: either the configuration if the last statement is a Configuration else None
    """
    # first import the config file as module, retrieve all the globals
    module_name = config_path.stem
    loader = SourceFileLoader(module_name, str(config_path))
    spec = spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    config_globals = {k: module.__getattribute__(k) for k in module.__dict__}
    script = open(config_path, 'r').read()
    stmts = list(ast.iter_child_nodes(ast.parse(script)))
    if not stmts:
        return None

    if isinstance(stmts[-1], ast.Expr):
        last_expr: ast.Expr = cast(ast.Expr, stmts[-1])

        if len(stmts) > 1:
            ast_module: mod = ast.Module(body=stmts[:-1], type_ignores=[])
            compiled = compile(ast_module, filename="<ast>", mode="exec")
            exec(compiled, config_globals)
        # then we eval the last one
        ast_expression: mod = ast.Expression(body=last_expr.value, type_ignores=[])
        compiled = compile(ast_expression, filename="<ast>", mode="eval")
        value = eval(compiled, config_globals)
        if isinstance(value, Configuration):
            return value

    return None


async def configuration_from_python(path: Path) -> Configuration:
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

    config = try_last_expression_as_config(final_path)
    if config:
        return config

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

    return config_data
