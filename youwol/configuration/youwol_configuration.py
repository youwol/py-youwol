import inspect
from datetime import datetime
import json
import os
import sys
import traceback
import pprint
from pathlib import Path
from typing import List, Dict, Any, Union, NamedTuple, Optional

from pydantic import ValidationError

from services.backs.assets_gateway.models import DefaultDriveResponse
from youwol.web_socket import WebSocketsCache

from youwol.errors import HTTPResponseException
from youwol.main_args import get_main_arguments
from youwol.utils_paths import parse_json
from youwol.models import ActionStep

from youwol.configuration.user_configuration import (UserInfo, get_public_user_auth_token)
from youwol.configurations import get_full_local_config
from youwol.context import Context

from youwol.configuration.configuration_validation import (
    ConfigurationLoadingStatus, ConfigurationLoadingException,
    CheckConfPath, CheckValidTextFile, CheckValidPythonScript, CheckValidConfigParametersFunction,
    CheckValidConfigurationFunction, CheckSystemFolderWritable, CheckDatabasesFolderHealthy, CheckSecretPathExist,
    CheckSecretHealthy
    )
from youwol.configuration.models_base import ErrorResponse, format_unknown_error, ConfigParameters
from youwol.configuration.paths import PathsBook
from youwol.configuration.user_configuration import (
    UserConfiguration, General,
    RemoteGateway,
    )


class DeadlinedCache(NamedTuple):

    value: any
    deadline: float
    dependencies: Dict[str, str]

    def is_valid(self, dependencies) -> bool:

        for k, v in self.dependencies.items():
            if k not in dependencies or dependencies[k] != v:
                return False
        margin = self.deadline - datetime.timestamp(datetime.now())
        return margin > 0


class YouwolConfiguration(NamedTuple):

    http_port: int

    userEmail: Optional[str]
    selectedRemote: Optional[str]

    userConfig: UserConfiguration

    pathsBook: PathsBook


    configurationParameters: ConfigParameters = ConfigParameters(parameters={})

    cache: Dict[str, Any] = {}
    private_cache: Dict[str, Any] = {}

    tokensCache: List[DeadlinedCache] = []

    def get_user_info(self) -> UserInfo:

        users_info = parse_json(self.userConfig.general.usersInfo)['users']

        if self.userEmail in users_info:
            data = users_info[self.userEmail]
            return UserInfo(**data)

        raise Exception(f"User '{self.userEmail}' not reference in '{str(self.userConfig.general.usersInfo)}")

    def get_remote_info(self) -> Optional[RemoteGateway]:

        info = parse_json(self.userConfig.general.remotesInfo)['remotes']

        if self.selectedRemote in info:
            data = info[self.selectedRemote]
            return RemoteGateway(**data)

        return None

    async def get_auth_token(self, context: Context, use_cache=True):
        username = self.userEmail
        remote = self.get_remote_info()
        dependencies = {"username": username, "host": remote.host, "type": "auth_token"}
        cached_token = next((c for c in self.tokensCache if c.is_valid(dependencies)), None)
        if use_cache and cached_token:
            return cached_token.value

        secrets = parse_json(self.userConfig.general.secretsFile)
        if username not in secrets:
            raise RuntimeError(f"Can not find {username} in {str(self.userConfig.general.secretsFile)}")

        pwd = secrets[username]['password']
        try:
            access_token = await get_public_user_auth_token(
                username=username,
                pwd=pwd,
                client_id=remote.metadata['keycloakClientId'],
                openid_host=self.userConfig.general.openid_host
                )
        except Exception as e:
            raise RuntimeError(f"Can not authorize from email/pwd provided in " +
                               f"{str(self.userConfig.general.secretsFile)} (error:{e})")

        deadline = datetime.timestamp(datetime.now()) + 1 * 60 * 60 * 1000
        self.tokensCache.append(DeadlinedCache(value=access_token, deadline=deadline, dependencies=dependencies))

        await context.info(step=ActionStep.STATUS, content="Access token renewed",
                           json={"host": remote.host, "access_token": access_token})
        return access_token

    async def get_default_drive(self, context: Context) -> DefaultDriveResponse:

        if self.private_cache.get("default-drive"):
            return self.private_cache.get("default-drive")
        default_drive = await LocalClients.get_assets_gateway_client(context).get_default_user_drive()
        self.private_cache["default-drive"] = DefaultDriveResponse(**default_drive)
        return DefaultDriveResponse(**default_drive)


class YouwolConfigurationFactory:

    __cached_config: YouwolConfiguration = None

    @staticmethod
    async def switch(path: Union[str, Path],
                     context: Context) -> ConfigurationLoadingStatus:

        async with context.start("Switch Configuration") as ctx:
            path = Path(path)
            cached = YouwolConfigurationFactory.__cached_config
            conf, status = await safe_load(path=path, params_values={},
                                           user_email=cached.userEmail,
                                           selected_remote=cached.selectedRemote,
                                           context=context)
            if not conf:
                errors = [c.dict() for c in status.checks if isinstance(c.status, ErrorResponse)]
                await ctx.abort(content='Failed to switch configuration',
                                json={
                                    "first error": next(e for e in errors),
                                    "errors": errors,
                                    "all checks": [c.dict() for c in status.checks]})
                return status
            await ctx.info(step=ActionStep.STATUS, content='Switched to new conf. successful', json=status.dict())
            await YouwolConfigurationFactory.trigger_on_load(config=conf)
            YouwolConfigurationFactory.__cached_config = conf
        return status

    @staticmethod
    async def get():
        cached = YouwolConfigurationFactory.__cached_config
        config = cached or await YouwolConfigurationFactory.init()
        return config

    @staticmethod
    async def reload(params_values: Dict[str, Any] = None):

        params_values = params_values or {}
        cached = YouwolConfigurationFactory.__cached_config
        cached_params = cached.configurationParameters.get_values() if cached.configurationParameters else {}
        params_values = {**cached_params, **params_values}
        conf, status = await safe_load(
            path=cached.pathsBook.config,
            params_values=params_values,
            user_email=cached.userEmail,
            selected_remote=cached.selectedRemote
            )
        if not conf:
            return status

        YouwolConfigurationFactory.__cached_config = conf
        return status

    @staticmethod
    async def login(email: Union[str, None], remote_name: Union[str, None], context: Context = None):

        conf = YouwolConfigurationFactory.__cached_config
        email, remote_name = await login(email, remote_name, conf.userConfig.general, context)

        new_conf = YouwolConfiguration(
            userConfig=conf.userConfig,
            userEmail=email,
            selectedRemote=remote_name,
            pathsBook=conf.pathsBook,
            projects=conf.projects,
            configurationParameters=conf.configurationParameters,
            http_port=get_main_arguments().port,
            cache={}
            )
        YouwolConfigurationFactory.__cached_config = new_conf
        await YouwolConfigurationFactory.trigger_on_load(config=conf)
        return new_conf

    @staticmethod
    async def init():
        path = (await get_full_local_config()).starting_yw_config_path
        conf, status = await safe_load(path=path, params_values={}, user_email=None, selected_remote=None)
        if not conf:
            for check in status.checks:
                if isinstance(check.status, ErrorResponse):
                    pprint.pprint(check)
            raise ConfigurationLoadingException(status)

        YouwolConfigurationFactory.__cached_config = conf
        await YouwolConfigurationFactory.trigger_on_load(config=conf)
        return YouwolConfigurationFactory.__cached_config

    @staticmethod
    def clear_cache():

        conf = YouwolConfigurationFactory.__cached_config
        new_conf = YouwolConfiguration(
            userConfig=conf.userConfig,
            userEmail=conf.userEmail,
            selectedRemote=conf.selectedRemote,
            pathsBook=conf.pathsBook,
            projects=conf.projects,
            configurationParameters=conf.configurationParameters,
            http_port=get_main_arguments().port,
            cache={}
            )
        YouwolConfigurationFactory.__cached_config = new_conf

    @staticmethod
    async def trigger_on_load(config: YouwolConfiguration):

        context = Context(config=config, web_socket=WebSocketsCache.environment)
        if not config.userConfig.events or not config.userConfig.events.onLoad:
            return
        on_load_cb = config.userConfig.events.onLoad

        data = await on_load_cb(config, context) \
            if inspect.iscoroutinefunction(on_load_cb) \
            else on_load_cb(config, context)

        await context.info(step=ActionStep.STATUS, content="Applied onLoad event's callback", json=data)


async def yw_config() -> YouwolConfiguration:
    return await YouwolConfigurationFactory.get()


async def login(
        user_email: Union[str, None],
        selected_remote: Union[str, None],
        general: General,
        context: Union[Context, None]) -> (str, str):

    starting_user = get_main_arguments().email
    if user_email is None and starting_user is not None:
        user_email = starting_user

    if user_email is None:
        users_info = parse_json(general.usersInfo)
        if 'default' in users_info['policies']:
            user_email = users_info['policies']["default"]

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
    if user_email not in parse_json(general.usersInfo)['users']:
        context and await context.info(
            ActionStep.STATUS,
            f"User {user_email} not registered in {general.usersInfo}: switch user",
            json={"user_email": user_email, 'usersInfo': parse_json(general.usersInfo)
                  }
            )
        return await login(user_email=None, selected_remote=selected_remote, general=general, context=context)

    if general.remotesInfo is None:
        return user_email, None

    remotes_info = parse_json(general.remotesInfo)
    remotes = remotes_info['remotes']

    if selected_remote in remotes:
        return user_email, selected_remote

    if "policies" in remotes_info and "default" in remotes_info['policies']:
        default = remotes_info['policies']['default']
        if default in remotes:
            return user_email, default

    return user_email, None


async def safe_load(
        path: Path,
        params_values: Dict[str, Any],
        user_email:  Union[str, None],
        selected_remote:  Union[RemoteGateway, None],
        context: Union[Context, None] = None,
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
                check_secret_healthy
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
            reason=f"Parsing the object returned by the function 'async def configuration(...)' " +
                   "to UserConfiguration failed.",
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
        config=path,
        databases=Path(user_config.general.databasesFolder),
        system=Path(user_config.general.systemFolder),
        secrets=Path(secrets_file) if secrets_file else None,
        usersInfo=Path(user_config.general.usersInfo),
        remotesInfo=Path(user_config.general.remotesInfo)
        )

    if not os.access(paths_book.system.parent, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system.parent)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."]
            )
        return None, get_status()

    if not paths_book.system.exists():
        os.mkdir(paths_book.system)

    check_system_folder_writable.status = True

    if not os.access(paths_book.system, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."]
            )
        return None, get_status()

    if not paths_book.store_node_modules.exists():
        os.mkdir(paths_book.store_node_modules)

    if not paths_book.packages_cache_path.exists():
        open(paths_book.packages_cache_path, "w").write(json.dumps({}))

    if not paths_book.usersInfo.exists():
        open(paths_book.usersInfo, "w").write(json.dumps({"policies": {}, "users": {}}))

    if not paths_book.remotesInfo.exists():
        open(paths_book.remotesInfo, "w").write(json.dumps({"remotes": {}}))

    if not paths_book.secrets.exists():
        base_secrets = {
            "identities": {}
            }
        open(paths_book.secrets, "w").write(json.dumps(base_secrets))

    if not paths_book.packages_cache_path.exists():
        open(paths_book.secrets, "w").write(json.dumps({}))

    user_email, selected_remote = await login(
        user_email=user_email,
        selected_remote=selected_remote,
        general=user_config.general,
        context=context)

    return YouwolConfiguration(
            http_port=get_main_arguments().port,
            userEmail=user_email,
            selectedRemote=selected_remote,
            userConfig=user_config,
            configurationParameters=parameters,
            pathsBook=paths_book,
        ), get_status(validated=True)
