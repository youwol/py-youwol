import json
import os
import sys
import traceback
from pathlib import Path
from typing import List, Dict, Any

from pydantic import BaseModel, ValidationError

from youwol.configuration.models_base import Check, ErrorResponse, format_unknown_error, ConfigParameters
from youwol.configuration.paths import PathsBook
from youwol.configuration.user_configuration import YouwolConfiguration, UserConfiguration, LocalClients, General
from youwol.errors import HTTPResponseException
from youwol.main_args import get_main_arguments
from youwol.utils_paths import parse_json

from youwol_utils import CdnClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.treedb.treedb import TreeDbClient

from youwol.configurations import configuration as py_yw_config


class CheckConfPath(Check):
    name: str = "Configuration path exist?"


class CheckValidTextFile(Check):
    name: str = "Valid text file?"


class CheckValidPythonScript(Check):
    name: str = "Valid python script?"


class CheckValidConfigParametersFunction(Check):
    name: str = "configuration_parameters function valid?"


class CheckValidConfigurationFunction(Check):
    name: str = "Configuration function valid?"


class CheckSystemFolderWritable(Check):
    name: str = "System folder is writable?"


class CheckDatabasesFolderHealthy(Check):
    name: str = "Databases folder is healthy?"


class CheckSecretPathExist(Check):
    name: str = "Secrets path is valid?"


class CheckSecretHealthy(Check):
    name: str = "Secrets are valid?"


class CheckDefaultPublishPath(Check):
    name: str = "Default publish path is valid?"


class ConfigurationLoadingStatus(BaseModel):

    path: str
    validated: bool = False
    checks: List[Check]


class ConfigurationLoadingException(HTTPResponseException):

    def __init__(self, status: ConfigurationLoadingStatus):

        check = next(check for check in status.checks if isinstance(check.status, ErrorResponse))
        super().__init__(
            status_code=500,
            title=check.name,
            descriptions=[
                "Loading and parsing the configuration file failed.",
                f"Path of the config file: {status.path}"
            ],
            hints=check.status.hints,
            footer="Try reloading the page after the issue resolution")
        self.status = status


async def login(user_email: str, general: General):

    if user_email is None:
        users_info = parse_json(general.usersInfo)
        if 'default' in users_info:
            user_email = users_info["default"]

    if user_email is None:

        raise HTTPResponseException(
            status_code=401,
            title="User has not been identified",
            descriptions=[f"make sure your users info file ({general.usersInfo}) contains"],
            hints=[
                "a 'default' field is pointing to the desired default email address",
                "the desired default email address is associated to an identity"
                ]
            )
    return user_email


async def safe_load(
        path: Path,
        params_values: Dict[str, Any],
        user_email: str = None
        ) -> (YouwolConfiguration, ConfigurationLoadingStatus):

    check_conf_path = CheckConfPath()
    check_valid_text = CheckValidTextFile()
    check_valid_python = CheckValidPythonScript()
    check_valid_conf_param_fct = CheckValidConfigParametersFunction()
    check_valid_conf_fct = CheckValidConfigurationFunction()
    check_system_folder_writable = CheckSystemFolderWritable()
    check_database_folder_healthy = CheckDatabasesFolderHealthy()
    check_secret_exists = CheckSecretPathExist()
    check_secret_healthy = CheckSecretHealthy()
    check_default_publish = CheckDefaultPublishPath()

    def get_status(validated: bool = False):
        return ConfigurationLoadingStatus(
            path=str(path),
            validated=validated,
            checks=[
                check_conf_path,
                check_valid_text,
                check_valid_python,
                check_valid_conf_param_fct,
                check_valid_conf_fct,
                check_system_folder_writable,
                check_database_folder_healthy,
                check_secret_exists,
                check_secret_healthy,
                check_default_publish
                ]
            )

    if not path.exists():
        check_conf_path.status = ErrorResponse(
            reason="The specified configuration path does not exist.",
            hints=[f"Double check the location '{str(path)}' do exist."]
            )
        return None, get_status()

    check_conf_path.status = True
    try:
        source = Path(path).read_text()
    except Exception as e:
        print(e)
        check_valid_text.status = ErrorResponse(
            reason="The specified configuration path is not a valid text file.",
            hints=[f"Double check the file at location '{str(path)}' is a valid text file."]
            )
        return None, get_status()

    check_valid_text.status = True
    try:
        scope = {}
        exec(source, scope)
    except SyntaxError as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        line_number = err.lineno
        check_valid_python.status = ErrorResponse(
            reason=f"There is a syntax error in the python file.",
            hints=[f"{error_class} at line {line_number}: {detail}"]
            )
        return None, get_status()
    except Exception as err:
        check_valid_python.status = format_unknown_error(
            reason=f"There was an exception parsing your python file.",
            error=err)
        return None, get_status()

    check_valid_python.status = True

    if 'configuration' not in scope:
        check_valid_conf_fct.status = ErrorResponse(
                reason=f"The configuration file need to define a 'configuration' function.",
                hints=[f"""Make sure the configuration file include a function with signature :
                'async def configuration(main_args: MainArguments)."""])
        return None, get_status()

    #  Look up for 'configuration_parameters' if any
    parameters = None
    if 'configuration_parameters' in scope:
        try:
            parameters = await scope.get('configuration_parameters')()
            parameters = parameters.with_updates(params_values)
        except Exception as err:
            check_valid_conf_param_fct.status = format_unknown_error(
                reason="Failed to retrieved configuration parameters when executing 'configuration_parameters'",
                error=err
                )
            return None, get_status()

    if parameters and not isinstance(parameters, ConfigParameters):
        check_valid_conf_param_fct.status = ErrorResponse(
            reason="The function 'configuration_parameters' must return an instance of 'ConfigParameters'",
            hints=[""]
            )
        return None, get_status()

    check_valid_conf_param_fct.status = True

    try:
        main_args = get_main_arguments()
        user_config: UserConfiguration = \
            await scope.get('configuration')(main_args, parameters.get_values()) if parameters is not None else \
            await scope.get('configuration')(main_args)

        if not isinstance(user_config, UserConfiguration):
            check_valid_conf_fct.status = ErrorResponse(
                reason=f"The function 'configuration' must return an instance of type 'UserConfiguration'",
                hints=[f"You can have a look at the default_config_yw.py located in 'py-youwol/system'"])
            return None, get_status()

    except ValidationError as err:
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"Parsing the 'configuration' object to UserConfiguration failed.",
            hints=[f"{str(err)}"])
        return None, get_status()
    except TypeError as err:

        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"Misused of configuration function",
            hints=[f"details: {str(err)}"])
        return None, get_status()
    except FileNotFoundError as err:
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"File or directory not found: {err.filename}",
            hints=["Make sure the intended path is correct. "
                   "You may also want to create the directory in your config. file"])
        return None, get_status()
    except Exception as err:
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)
        check_valid_conf_fct.status = format_unknown_error(
                reason=f"There was an exception calling the 'configuration'.",
                error=err)
        return None, get_status()

    check_valid_conf_fct.status = True

    secrets_file = user_config.general.secretsFile
    paths_book = PathsBook(
        config_path=path,
        data_path=Path(user_config.general.databasesFolder),
        system_path=Path(user_config.general.systemFolder),
        secret_path=Path(secrets_file) if secrets_file else None,
        usersInfo=Path(user_config.general.usersInfo),
        pinnedPaths={k: Path(v) for k, v in user_config.general.pinnedPaths.items()}
        )

    if not os.access(paths_book.system_path.parent, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system_path.parent)}",
            hints=[f"Ensure you have permission to write in {paths_book.system_path}."]
            )
        return None, get_status()

    if not paths_book.system_path.exists():
        os.mkdir(paths_book.system_path)

    check_system_folder_writable.status = True

    if not os.access(paths_book.system_path, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system_path)}",
            hints=[f"Ensure you have permission to write in {paths_book.system_path}."]
            )
        return None, get_status()

    if not paths_book.store_node_modules.exists():
        os.mkdir(paths_book.store_node_modules)

    if not paths_book.packages_cache_path.exists():
        open(paths_book.packages_cache_path, "w").write(json.dumps({}))

    if not paths_book.usersInfo.exists():
        open(paths_book.usersInfo, "w").write(json.dumps({}))

    path_default_publish = user_config.general.defaultPublishLocation
    if len(path_default_publish.split('/')) < 2:
        check_default_publish.status = ErrorResponse(
            reason=f"The default publish path 'defaultPublishLocation' needs to at least specify group and drive names"
                   + ", e.g.: {group_name}/{drive_name}",
            hints=[f"The default publish location if 'defaultPublishLocation' is not specified is "
                   + "'private/default-drive'"]
            )
        return None, get_status()

    if not paths_book.secret_path.exists():
        base_secrets = {
            "identities": {}
            }
        open(paths_book.secret_path, "w").write(json.dumps(base_secrets))

    if not paths_book.packages_cache_path.exists():
        open(paths_book.secret_path, "w").write(json.dumps({}))

    base_path = f"http://localhost:{py_yw_config.http_port}/api"
    assets_client = AssetsClient(url_base=f"{base_path}/assets-backend")
    treedb_client = TreeDbClient(url_base=f"{base_path}/treedb-backend")
    flux_client = FluxClient(url_base=f"{base_path}/flux-backend")
    cdn_client = CdnClient(url_base=f"{base_path}/cdn-backend")
    assets_gateway_client = AssetsGatewayClient(url_base=f"{base_path}/assets-gateway")

    user_email = await login(user_email, user_config.general)

    return YouwolConfiguration(
            http_port=get_main_arguments().port,
            userEmail=user_email,
            userConfig=user_config,
            configurationParameters=parameters,
            pathsBook=paths_book,
            localClients=LocalClients(
                assets_client=assets_client,
                treedb_client=treedb_client,
                flux_client=flux_client,
                cdn_client=cdn_client,
                assets_gateway_client=assets_gateway_client
                ),
            cache={}
        ), get_status(validated=True)
