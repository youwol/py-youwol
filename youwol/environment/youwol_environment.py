import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Awaitable, List

from colorama import Fore, Style
from cowpy import cow
from pydantic import BaseModel

import youwol
from youwol.configuration.configuration_validation import (
    ConfigurationLoadingStatus, ConfigurationLoadingException,
    CheckSystemFolderWritable, CheckDatabasesFolderHealthy
)
from youwol.configuration.models_config import Events
from youwol.configuration.models_config_middleware import CustomMiddleware
from youwol.environment.clients import LocalClients
from youwol.environment.config_from_module import configuration_from_python
from youwol.environment.configuration_handler import ConfigurationHandler
from youwol.environment.models import RemoteGateway, ApiConfiguration, Projects
from youwol.environment.models_project import ErrorResponse
from youwol.environment.paths import PathsBook, ensure_config_file_exists_or_create_it
from youwol.main_args import get_main_arguments, MainArguments
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.routers.custom_backends import install_routers
from youwol.routers.custom_commands.models import Command
from youwol.web_socket import WsDataStreamer
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.context import Context, ContextFactory, InMemoryReporter
from youwol_utils.http_clients.tree_db_backend import DefaultDriveResponse
from youwol_utils.servers.fast_api import FastApiRouter
from youwol_utils.utils_paths import parse_json


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
    httpPort: int
    redirectBasePath: str
    events: Events
    cdnAutomaticUpdate: bool
    customDispatches: List[AbstractDispatch]
    customMiddlewares: List[CustomMiddleware]

    projects: Projects
    commands: Dict[str, Command]

    selectedRemote: str
    selectedUser: Optional[str]
    remotes: List[RemoteGateway]

    pathsBook: PathsBook
    portsBook: Dict[str, int] = {}
    routers: List[FastApiRouter] = []
    cache: Dict[str, Any] = {}
    private_cache: Dict[str, Any] = {}

    tokensCache: List[DeadlinedCache] = []

    def reset_cache(self):
        self.cache = {}
        self.private_cache = {}

    def get_users_list(self) -> List[str]:
        return [user.username for user in self.get_remote_info().users]

    def get_remote_info(self, remote_host: str = None) -> Optional[RemoteGateway]:

        if not remote_host:
            remote_host = self.selectedRemote

        candidates = [remote for remote in self.remotes if remote.host == remote_host]
        if len(candidates) > 0:
            return candidates[0]

        return None

    async def get_auth_token(self, context: Context, remote_host: str = None, username: str = None):
        username = username if username else self.selectedUser
        remote = self.get_remote_info(remote_host)
        dependencies = {"username": username, "host": remote.host, "type": "auth_token"}
        cached_token = next((c for c in self.tokensCache if c.is_valid(dependencies)), None)
        if cached_token and not remote_host:
            return cached_token.value

        try:
            access_token = (await OidcConfig(remote.openidBaseUrl).for_client(remote.openidClient).direct_flow(
                username=username,
                password=([user.password for user in remote.users if user.username == username][0])
            ))['access_token']
        except Exception as e:
            raise RuntimeError(f"Can not get access token for user '{username}' : {e}")

        deadline = datetime.timestamp(datetime.now()) + 1 * 60 * 60 * 1000
        self.tokensCache.append(DeadlinedCache(value=access_token, deadline=deadline, dependencies=dependencies))

        await context.info(text="Access token renewed",
                           data={"host": remote.host, "access_token": access_token})
        return access_token

    async def get_default_drive(self, context: Context) -> DefaultDriveResponse:

        if self.private_cache.get("default-drive"):
            return self.private_cache.get("default-drive")
        env = await context.get('env', YouwolEnvironment)
        default_drive = await LocalClients \
            .get_assets_gateway_client(env).get_treedb_backend_router() \
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
- user: {self.selectedUser if self.selectedUser else 'dynamic'}
- remote : {self.selectedRemote}
- paths: {self.pathsBook}
- cdn packages count: {len(parse_json(self.pathsBook.local_cdn_docdb)['documents'])}
- assets count: {len(parse_json(self.pathsBook.local_assets_entities_docdb)['documents'])}
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
    async def reload(selected_user: Optional[str] = None, selected_remote: Optional[str] = None):
        cached = YouwolEnvironmentFactory.__cached_config
        conf = await safe_load(
            path=cached.pathsBook.config,
            selected_user=selected_user if selected_user else cached.selectedUser,
            selected_remote=selected_remote if selected_remote else cached.selectedRemote
        )

        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        YouwolEnvironmentFactory.__cached_config = conf
        return conf

    @staticmethod
    async def init():
        path = await get_yw_config_starter(get_main_arguments())
        conf = await safe_load(path=path, selected_user=None, selected_remote=None)

        YouwolEnvironmentFactory.__cached_config = conf
        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        return YouwolEnvironmentFactory.__cached_config

    @staticmethod
    def clear_cache():
        conf = YouwolEnvironmentFactory.__cached_config
        new_conf = YouwolEnvironment(
            redirectBasePath=conf.redirectBasePath,
            selectedUser=conf.selectedUser,
            selectedRemote=conf.selectedRemote,
            pathsBook=conf.pathsBook,
            httpPort=conf.httpPort,
            cache={},
            projects=conf.projects,
            commands=conf.commands,
            customDispatches=conf.customDispatches,
            customMiddlewares=conf.customMiddlewares,
            cdnAutomaticUpdate=conf.cdnAutomaticUpdate,
            events=conf.events,
            remotes=conf.remotes
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


async def safe_load(
        path: Path,
        selected_user: Optional[str],
        selected_remote: Optional[str],
) -> YouwolEnvironment:
    """
    Possible errors:
    - the user id saved in users-info.json is actually not the actual one (from remote env).
    => everything seems to work fine but the assets in remotes are not visible from local explorer
    """
    check_system_folder_writable = CheckSystemFolderWritable()
    check_database_folder_healthy = CheckDatabasesFolderHealthy()

    def get_status(validated: bool = False):
        return ConfigurationLoadingStatus(
            path=str(path),
            validated=validated,
            checks=[
                check_system_folder_writable,
                check_database_folder_healthy,
            ]
        )

    conf_handler: ConfigurationHandler = await configuration_from_python(path)

    paths_book = PathsBook(
        config=path,
        databases=Path(conf_handler.get_data_dir()),
        system=Path(conf_handler.get_cache_dir()),
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

    youwol_configuration = YouwolEnvironment(
        redirectBasePath=conf_handler.get_redirect_base_path(),
        httpPort=conf_handler.get_http_port(),
        portsBook=conf_handler.get_ports_book(),
        routers=conf_handler.get_routers(),
        selectedUser=selected_user if selected_user else conf_handler.get_selected_remote().defaultUser,
        selectedRemote=selected_remote if selected_remote else conf_handler.get_selected_remote().host,
        events=conf_handler.get_events(),
        cdnAutomaticUpdate=conf_handler.get_cdn_auto_update(),
        pathsBook=paths_book,
        projects=conf_handler.get_projects(),
        commands=conf_handler.get_commands(),
        customDispatches=conf_handler.get_dispatches(),
        customMiddlewares=conf_handler.get_middlewares(),
        remotes=[RemoteGateway.from_config(remote_config) for remote_config in conf_handler.get_remotes()]
    )
    return await conf_handler.customize(youwol_configuration)


async def get_yw_config_starter(main_args: MainArguments):
    (conf_path, exists) = ensure_config_file_exists_or_create_it(main_args.config_path)

    return conf_path


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
