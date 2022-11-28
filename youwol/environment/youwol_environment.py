import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Awaitable, List, Union

from colorama import Fore, Style
from cowpy import cow
from pydantic import BaseModel

import youwol
from youwol.environment import ImpersonateAuthConnection, BrowserAuthConnection
from youwol.environment.errors_handling import (
    ConfigurationLoadingStatus, ConfigurationLoadingException,
    CheckSystemFolderWritable, CheckDatabasesFolderHealthy, ErrorResponse
)

from youwol.environment.models import Events, RemoteConnection, Impersonation, Configuration, CustomMiddleware, \
    RemoteGateway, ApiConfiguration
from youwol.environment.models.models import ProjectsSanitized
from youwol.environment.config_from_module import configuration_from_python
from youwol.environment.paths import PathsBook, ensure_config_file_exists_or_create_it
from youwol.main_args import get_main_arguments, MainArguments
from youwol.routers.custom_backends import install_routers
from youwol.routers.custom_commands.models import Command
from youwol.web_socket import WsDataStreamer
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.context import Context, ContextFactory, InMemoryReporter
from youwol_utils.servers.fast_api import FastApiRouter
from youwol_utils.utils_paths import parse_json, ensure_dir_exists
from youwol.environment.paths import app_dirs


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
    events: Events
    customMiddlewares: List[CustomMiddleware]

    projects: ProjectsSanitized
    commands: Dict[str, Command]

    currentConnection: RemoteConnection

    remotes: List[RemoteGateway]
    impersonations: List[Impersonation]

    pathsBook: PathsBook
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
            remote_host = self.currentConnection.host

        candidates = [remote for remote in self.remotes if remote.host == remote_host]
        if len(candidates) > 0:
            return candidates[0]

        return None

    def get_user_info(self, user_id: str = None) -> Optional[Impersonation]:

        if not user_id:
            user_id = self.currentConnection.userId

        candidates = [user for user in self.impersonations if user.userId == user_id]
        if len(candidates) > 0:
            return candidates[0]

        return None

    async def get_auth_token(self, context: Context):
        remote = self.get_remote_info(self.currentConnection.host)
        user = self.get_user_info(self.currentConnection.userId)

        username = user.userName
        dependencies = {"username": username, "host": remote.host, "type": "auth_token"}
        cached_token = next((c for c in self.tokensCache if c.is_valid(dependencies)), None)
        if cached_token:
            return cached_token.value

        try:
            token = await OidcConfig(remote.openidBaseUrl).for_client(remote.openidClient).direct_flow(
                username=username,
                password=([user.password for user in remote.users if user.username == username][0])
            )
            access_token = token['access_token']
            expire = token['expires_in']
        except Exception as e:
            raise RuntimeError(f"Can not get access token for user '{username}' : {e}")

        deadline = datetime.timestamp(datetime.now()) + expire
        self.tokensCache.append(DeadlinedCache(value=access_token, deadline=deadline, dependencies=dependencies))

        await context.info(text="Access token renewed",
                           data={"host": remote.host, "access_token": access_token})
        return access_token

    def __str__(self):
        def str_middlewares():
            if len(self.customMiddlewares) != 0:
                return f"""
- list of middlewares:
{chr(10).join([f"  * {redirection}" for redirection in self.customMiddlewares])}
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
- user: {self.currentConnection.userId if isinstance(self.currentConnection, ImpersonateAuthConnection) else 'dynamic'}
- remote : {self.currentConnection.host}
- paths: {self.pathsBook}
- cdn packages count: {len(parse_json(self.pathsBook.local_cdn_docdb)['documents'])}
- assets count: {len(parse_json(self.pathsBook.local_assets_entities_docdb)['documents'])}
{str_middlewares()}
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
    async def reload(connection: Union[BrowserAuthConnection, ImpersonateAuthConnection] = None):
        cached = YouwolEnvironmentFactory.__cached_config
        conf = await safe_load(
            path=cached.pathsBook.config,
            remote_connection=connection or cached.currentConnection
        )

        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        YouwolEnvironmentFactory.__cached_config = conf
        return conf

    @staticmethod
    async def init():
        path = await get_yw_config_starter(get_main_arguments())
        conf = await safe_load(path=path)

        YouwolEnvironmentFactory.__cached_config = conf
        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        return YouwolEnvironmentFactory.__cached_config

    @staticmethod
    def clear_cache():
        conf = YouwolEnvironmentFactory.__cached_config
        new_conf = YouwolEnvironment(
            currentConnection=conf.currentConnection,
            pathsBook=conf.pathsBook,
            httpPort=conf.httpPort,
            cache={},
            projects=conf.projects,
            commands=conf.commands,
            customMiddlewares=conf.customMiddlewares,
            events=conf.events,
            remotes=conf.remotes,
            impersonations=conf.impersonations
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
            on_load_cb = config.events.onLoad(context)
            data = await on_load_cb if isinstance(on_load_cb, Awaitable) else on_load_cb
            await context.info(text="Applied onLoad event's callback", data=data)

        await install_routers(config.routers, context)
        await context.info(text="Additional routers installed")


async def yw_config() -> YouwolEnvironment:
    return await YouwolEnvironmentFactory.get()


async def safe_load(
        path: Path,
        remote_connection: Optional[RemoteConnection] = None
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

    config: Configuration = await configuration_from_python(path)
    system = config.system
    projects = config.projects
    customization = config.customization

    paths_book = PathsBook(
        config=path,
        databases=Path(system.localEnvironment.dataDir),
        system=Path(system.localEnvironment.cacheDir)
    )
    ensure_dir_exists(system.localEnvironment.cacheDir, root_candidates=app_dirs.user_cache_dir)

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

    def create_data_dir(final_path: Path):
        databases_zip = 'databases.zip'
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(get_main_arguments().youwol_path.parent / 'youwol_data' / databases_zip,
                        final_path.parent / databases_zip)

        with zipfile.ZipFile(final_path.parent / databases_zip, 'r') as zip_ref:
            zip_ref.extractall(final_path.parent)

        os.remove(final_path.parent / databases_zip)

    ensure_dir_exists(path=system.localEnvironment.dataDir, root_candidates=app_dirs.user_data_dir,
                      create=create_data_dir)

    return YouwolEnvironment(
        httpPort=system.httpPort,
        routers=customization.endPoints.routers,
        currentConnection=remote_connection or system.cloudEnvironments.defaultConnection,
        events=customization.events,
        pathsBook=paths_book,
        projects=ProjectsSanitized.from_config(projects),
        commands={c.name: c for c in customization.endPoints.commands},
        customMiddlewares=customization.middlewares,
        remotes=[RemoteGateway.from_config(cloud, system.cloudEnvironments.impersonations)
                 for cloud in system.cloudEnvironments.environments],
        impersonations=system.cloudEnvironments.impersonations
    )


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
