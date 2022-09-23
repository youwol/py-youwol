import json
import os
import shutil
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Dict, Any, Union, Optional, Awaitable, List

from colorama import Fore, Style
from cowpy import cow
from fastapi import HTTPException
from pydantic import BaseModel

import youwol
from youwol.configuration.config_from_module import configuration_from_python
from youwol.configuration.config_from_static_file import configuration_from_json
from youwol.configuration.configuration_handler import ConfigurationHandler
from youwol.configuration.configuration_validation import (
    ConfigurationLoadingStatus, ConfigurationLoadingException,
    CheckSystemFolderWritable, CheckDatabasesFolderHealthy, CheckSecretPathExist,
    CheckSecretHealthy
)
from youwol.configuration.defaults import default_platform_host
from youwol.configuration.models_config import JwtSource, ProjectTemplate
from youwol.configuration.models_k8s import PipelinesSourceInfo
from youwol.environment.clients import LocalClients
from youwol.environment.models import RemoteGateway, UserInfo, ApiConfiguration, Events
from youwol.environment.models_project import ErrorResponse
from youwol.environment.paths import PathsBook, ensure_config_file_exists_or_create_it
from youwol.main_args import get_main_arguments, MainArguments
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.routers.custom_backends import install_routers
from youwol.routers.custom_commands.models import Command
from youwol.utils.utils_low_level import get_public_user_auth_token
from youwol.web_socket import WsDataStreamer
from youwol_utils import retrieve_user_info
from youwol_utils.context import Context, ContextFactory, InMemoryReporter
from youwol_utils.http_clients.assets_gateway import DefaultDriveResponse
from youwol_utils.servers.fast_api import FastApiRouter
from youwol_utils.utils_paths import parse_json, write_json


class DeadlinedCache(BaseModel):
    value: Any
    deadline: float
    dependencies: Dict[str, str]

    def is_valid(self, dependencies) -> bool:

        for k, v in self.dependencies.items():
            if k not in dependencies or dependencies[k] != v:
                return False
        margin = self.deadline - datetime.timestamp(datetime.now())
        return margin > 0


class YouwolEnvironment(BaseModel):
    availableProfiles: List[str]
    httpPort: int
    jwtSource: JwtSource
    redirectBasePath: str
    openidHost: str
    events: Events
    activeProfile: Optional[str]
    cdnAutomaticUpdate: bool
    customDispatches: List[AbstractDispatch]

    projectTemplates: List[ProjectTemplate]
    commands: Dict[str, Command]

    userEmail: Optional[str]
    selectedRemote: Optional[str]

    pathsBook: PathsBook
    portsBook: Dict[str, int] = {}
    routers: List[FastApiRouter] = []
    cache: Dict[str, Any] = {}
    private_cache: Dict[str, Any] = {}

    tokensCache: List[DeadlinedCache] = []

    pipelinesSourceInfo: Optional[PipelinesSourceInfo]

    def reset_cache(self):
        self.cache = {}
        self.private_cache = {}

    def get_user_info(self) -> UserInfo:

        users_info = parse_json(self.pathsBook.usersInfo)['users']

        if self.userEmail in users_info:
            data = users_info[self.userEmail]
            return UserInfo(**data)

        raise RuntimeError(f"User '{self.userEmail}' not reference in '{str(self.pathsBook.usersInfo)}")

    def get_users_list(self) -> List[str]:
        users = list(parse_json(self.pathsBook.usersInfo)['users'].keys())
        return users

    def get_remote_info(self, remote_host: str = None) -> Optional[RemoteGateway]:

        info = parse_json(self.pathsBook.remotesInfo)['remotes']
        selected = remote_host or self.selectedRemote
        if selected in info:
            data = info[selected]
            return RemoteGateway(**data)

        return None

    async def get_auth_token(self, context: Context, remote_host: str = None, use_cache=True):
        username = self.userEmail
        remote = self.get_remote_info(remote_host)
        dependencies = {"username": username, "host": remote.host, "type": "auth_token"}
        cached_token = next((c for c in self.tokensCache if c.is_valid(dependencies)), None)
        if use_cache and cached_token and not remote_host:
            return cached_token.value

        secrets = parse_json(self.pathsBook.secrets)
        if username not in secrets:
            raise RuntimeError(f"Can not find {username} in {str(self.pathsBook.secrets)}")

        pwd = secrets[username]['password']
        try:
            access_token = await get_public_user_auth_token(
                username=username,
                pwd=pwd,
                client_id=remote.metadata['keycloakClientId'],
                openid_host=remote.host
            )
        except Exception as e:
            raise RuntimeError(f"Can not authorize from email/pwd provided in " +
                               f"{str(self.pathsBook.secrets)} (error:{e})")

        deadline = datetime.timestamp(datetime.now()) + 1 * 60 * 60 * 1000
        self.tokensCache.append(DeadlinedCache(value=access_token, deadline=deadline, dependencies=dependencies))

        await context.info(text="Access token renewed",
                           data={"host": remote.host, "access_token": access_token})
        return access_token

    async def get_default_drive(self, context: Context) -> DefaultDriveResponse:

        if self.private_cache.get("default-drive"):
            return self.private_cache.get("default-drive")
        env = await context.get('env', YouwolEnvironment)
        default_drive = await LocalClients\
            .get_assets_gateway_client(env)\
            .get_default_user_drive(headers=context.headers())

        self.private_cache["default-drive"] = DefaultDriveResponse(**default_drive)
        return DefaultDriveResponse(**default_drive)

    def __str__(self):
        def str_redirections():
            if len(self.customDispatches) != 0:
                return f"""
- list of redirections:
{chr(10).join([f"  * {redirection}" for redirection in self.customDispatches])}
"""
            else:
                return "- no redirections configured"

        def str_commands():
            if len(self.commands.keys()) != 0:
                return f"""
- list of custom commands:
{chr(10).join([f"  * http://localhost:{self.httpPort}/admin/custom-commands/{command}"
               for command in self.commands.keys()])}
"""
            else:
                return "- no custom command configured"

        def str_routers():
            if self.routers:
                return f"""
- list of additional routers:
{chr(10).join([f"  * {router.base_path}"
               for router in self.routers])}
"""
            else:
                return "- no custom command configured"

        return f"""Running with youwol: {youwol}
Configuration loaded from '{self.pathsBook.config}'
- user email: {self.userEmail}
- active profile: {self.activeProfile if self.activeProfile else "Default profile"}
- paths: {self.pathsBook}
- cdn packages count: {len(parse_json(self.pathsBook.local_cdn_docdb)['documents'])}
- assets count: {len(parse_json(self.pathsBook.local_docdb / 'assets' / 'entities' / 'data.json')['documents'])}
{str_redirections()}
{str_commands()}
{str_routers()}
"""


class YouwolEnvironmentFactory:
    __cached_config: Optional[YouwolEnvironment] = None

    @staticmethod
    async def get():
        cached = YouwolEnvironmentFactory.__cached_config
        config = cached or await YouwolEnvironmentFactory.init()
        return config

    @staticmethod
    async def reload(profile: str = None):
        cached = YouwolEnvironmentFactory.__cached_config
        conf = await safe_load(
            path=cached.pathsBook.config,
            profile=profile if profile is not None else cached.activeProfile,
            user_email=cached.userEmail,
            selected_remote=cached.selectedRemote
        )

        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        YouwolEnvironmentFactory.__cached_config = conf
        return conf

    @staticmethod
    async def login(email: Union[str, None], remote_name: Union[str, None], context: Context = None):
        conf = YouwolEnvironmentFactory.__cached_config
        email, remote_name = await login(email, remote_name, conf.pathsBook.usersInfo,
                                         conf.pathsBook.remotesInfo, context)

        new_conf = YouwolEnvironment(
            openidHost=conf.openidHost,
            jwtSource=conf.jwtSource,
            redirectBasePath=conf.redirectBasePath,
            userEmail=email,
            selectedRemote=remote_name,
            pathsBook=conf.pathsBook,
            httpPort=conf.httpPort,
            cache={},
            availableProfiles=conf.availableProfiles,
            commands=conf.commands,
            customDispatches=conf.customDispatches,
            projectTemplates=conf.projectTemplates,
            cdnAutomaticUpdate=conf.cdnAutomaticUpdate,
            events=conf.events
        )
        YouwolEnvironmentFactory.__cached_config = new_conf
        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        return new_conf

    @staticmethod
    async def init():
        path = await get_yw_config_starter(get_main_arguments())
        conf = await safe_load(path=path, profile=get_main_arguments().profile, user_email=None, selected_remote=None)

        YouwolEnvironmentFactory.__cached_config = conf
        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        return YouwolEnvironmentFactory.__cached_config

    @staticmethod
    def clear_cache():
        conf = YouwolEnvironmentFactory.__cached_config
        new_conf = YouwolEnvironment(
            openidHost=conf.openidHost,
            jwtSource=conf.jwtSource,
            redirectBasePath=conf.redirectBasePath,
            userEmail=conf.userEmail,
            selectedRemote=conf.selectedRemote,
            pathsBook=conf.pathsBook,
            httpPort=conf.httpPort,
            cache={},
            availableProfiles=conf.availableProfiles,
            commands=conf.commands,
            customDispatches=conf.customDispatches,
            cdnAutomaticUpdate=conf.cdnAutomaticUpdate,
            projectTemplates=conf.projectTemplates,
            events=conf.events
        )
        YouwolEnvironmentFactory.__cached_config = new_conf

    @staticmethod
    async def trigger_on_load(config: YouwolEnvironment):
        context = ContextFactory.get_instance(
            logs_reporter=InMemoryReporter(),
            data_reporter=WsDataStreamer(),
            request=None
        )
        if config.events and config.events.onLoad:
            on_load_cb = config.events.onLoad(config, context)
            data = await on_load_cb if isinstance(on_load_cb, Awaitable) else on_load_cb
            await context.info(text="Applied onLoad event's callback", data=data)

        await install_routers(config.routers, context)
        await context.info(text="Additional routers installed")


async def yw_config() -> YouwolEnvironment:
    return await YouwolEnvironmentFactory.get()


async def login(
        user_email: Union[str, None],
        selected_remote: Union[str, None],
        users_info_path: Path,
        remotes_info: Path,
        context: Union[Context, None]) -> (str, str):
    if user_email is None:
        users_info = parse_json(users_info_path)
        if 'default' in users_info['policies']:
            user_email = users_info['policies']["default"]

    if user_email is None:
        raise HTTPException(
            status_code=401,
            detail=f"User has not been identified, make sure it is defined in users info file ({users_info_path})"
        )
    if user_email not in parse_json(users_info_path)['users']:
        context and context.info(
            text=f"User {user_email} not registered in {users_info_path}: switch user",
            data={"user_email": user_email, 'usersInfo': parse_json(users_info_path)
                  }
        )
        return await login(user_email=None, selected_remote=selected_remote, users_info_path=users_info_path,
                           remotes_info=remotes_info,
                           context=context)

    if remotes_info is None:
        return user_email, None

    remotes_info = parse_json(remotes_info)
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
        profile: str,
        user_email: Optional[str],
        selected_remote: Optional[RemoteGateway],
        context: Optional[Context] = None,
) -> YouwolEnvironment:
    """
    Possible errors:
    - the user id saved in users-info.json is actually not the actual one (from remote env).
    => everything seems to work fine but the assets in remotes are not visible from local explorer
    """
    check_system_folder_writable = CheckSystemFolderWritable()
    check_database_folder_healthy = CheckDatabasesFolderHealthy()
    check_secret_exists = CheckSecretPathExist()
    check_secret_healthy = CheckSecretHealthy()

    def get_status(validated: bool = False):
        return ConfigurationLoadingStatus(
            path=str(path),
            validated=validated,
            checks=[
                check_system_folder_writable,
                check_database_folder_healthy,
                check_secret_exists,
                check_secret_healthy
            ]
        )

    loaders = {
        ".py": configuration_from_python,
        ".json": configuration_from_json
    }

    try:
        conf_handler: ConfigurationHandler = await loaders[path.suffix](path, profile)
    except KeyError as k:
        print(f"Unknown suffix : ${k}")
        raise ConfigurationLoadingException(get_status(False))

    paths_book = PathsBook(
        config=path,
        databases=Path(conf_handler.get_data_dir()),
        system=Path(conf_handler.get_cache_dir()),
        secrets=Path(conf_handler.get_config_dir() / Path("secrets.json")),
        usersInfo=Path(conf_handler.get_config_dir() / Path("users-info.json")),
        remotesInfo=Path(conf_handler.get_config_dir() / Path("remotes-info.json")),
        projects=conf_handler.get_projects_dirs(),
        additionalPythonScrPaths=conf_handler.get_additional_python_src_paths()
    )

    if not os.access(paths_book.system.parent, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system.parent)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."]
        )
        raise ConfigurationLoadingException(get_status(False))

    if not paths_book.system.exists():
        os.mkdir(paths_book.system)

    check_system_folder_writable.status = True

    if not os.access(paths_book.system, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."]
        )
        raise ConfigurationLoadingException(get_status(False))

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
        users_info_path=paths_book.usersInfo,
        remotes_info=paths_book.remotesInfo,
        context=context)

    youwol_configuration = YouwolEnvironment(
        activeProfile=conf_handler.get_profile(),
        jwtSource=conf_handler.get_jwt_source(),
        availableProfiles=conf_handler.get_available_profiles(),
        redirectBasePath=conf_handler.get_redirect_base_path(),
        openidHost=conf_handler.get_openid_host(),
        httpPort=conf_handler.get_http_port(),
        portsBook=conf_handler.get_ports_book(),
        routers=conf_handler.get_routers(),
        userEmail=user_email,
        selectedRemote=selected_remote,
        events=conf_handler.get_events(),
        cdnAutomaticUpdate=conf_handler.get_cdn_auto_update(),
        pathsBook=paths_book,
        commands=conf_handler.get_commands(),
        customDispatches=conf_handler.get_dispatches(),
        projectTemplates=conf_handler.get_project_templates(),
        pipelinesSourceInfo=conf_handler.get_pipelines_source_info()
    )
    return await conf_handler.customize(youwol_configuration)


async def get_yw_config_starter(main_args: MainArguments):
    (conf_path, exists) = ensure_config_file_exists_or_create_it(main_args.config_path)

    if not exists:
        await first_run(conf_path, main_args)

    return conf_path


async def first_run(conf_path, main_args):
    resp = input("No config path has been provided as argument (using --conf),"
                 f" and no file found in the default folder.\n"
                 "Do you want to create a new workspace with default settings (y/N)")
    # Ask to create fresh workspace with default settings
    if not (resp == 'y' or resp == 'Y'):
        print("Exit youwol")
        exit()
    # create the default identities
    email = input("Your email address?")
    pwd = getpass("Your YouWol password?")
    print(f"Pass : {pwd}")
    token = None
    try:
        token = await get_public_user_auth_token(username=email, pwd=pwd, client_id='public-user',
                                                 openid_host=default_platform_host)
        print("token", token)
    except HTTPException as e:
        print(f"Can not retrieve authentication token:\n\tstatus code: {e.status_code}\n\tdetail:{e.detail}")
        exit(1)
    user_info = None
    try:
        user_info = await retrieve_user_info(auth_token=token, openid_host=default_platform_host)
        print("user_info", user_info)
    except HTTPException as e:
        print(f"Can not retrieve user info:\n\tstatus code: {e.status_code}\n\tdetail:{e.detail}")
        exit(1)
    shutil.copyfile(main_args.youwol_path.parent / 'youwol_data' / 'remotes-info.json',
                    conf_path.parent / 'remotes-info.json')
    if not (conf_path.parent / 'secrets.json').exists():
        write_json({email: {'password': pwd}}, conf_path.parent / 'secrets.json')
    user_info = {
        "policies": {"default": email},
        "users": {
            email: {
                "id": user_info['sub'],
                "name": user_info['name'],
                "memberOf": user_info['memberof'],
                "email": user_info['email']
            }
        }
    }
    if not (conf_path.parent / 'users-info.json').exists():
        write_json(user_info, conf_path.parent / 'users-info.json')


def print_invite(conf: YouwolEnvironment, shutdown_script_path: Optional[Path]):
    print(f"""{Fore.GREEN}Configuration loaded successfully{Style.RESET_ALL}.
""")
    print(conf)
    msg = cow.milk_random_cow(f"""
All good, you can now browse to
http://localhost:{conf.httpPort}/applications/@youwol/platform/latest
""")
    print(msg)
    if shutdown_script_path is not None:
        print()
        print(f"Py-youwol will run in background. Use {shutdown_script_path} to stop it :")
        print(f"$ sh {shutdown_script_path}")


api_configuration = ApiConfiguration(open_api_prefix="", base_path="")
