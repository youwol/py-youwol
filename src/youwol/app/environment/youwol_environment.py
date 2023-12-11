# standard library
import importlib.metadata
import json
import os

from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Any, Awaitable, Dict, List, Optional

# third parties
from colorama import Fore, Style
from cowpy import cow
from pydantic import BaseModel

# Youwol
import youwol

# Youwol application
from youwol.app.main_args import MainArguments, get_main_arguments
from youwol.app.routers.custom_backends import install_routers
from youwol.app.web_socket import WsDataStreamer

# Youwol utilities
from youwol.utils.clients.oidc.tokens_manager import TokensStorage
from youwol.utils.context import ContextFactory, InMemoryReporter
from youwol.utils.servers.fast_api import FastApiRouter
from youwol.utils.utils_paths import ensure_dir_exists

# relative
from .config_from_module import configuration_from_python
from .errors_handling import (
    CheckDatabasesFolderHealthy,
    CheckSystemFolderWritable,
    ConfigurationLoadingException,
    ConfigurationLoadingStatus,
    ErrorResponse,
)
from .models import (
    ApiConfiguration,
    Configuration,
    Connection,
    CustomMiddleware,
    Events,
)
from .models.models_config import (
    Authentication,
    CloudEnvironment,
    Command,
    ExplicitProjectsFinder,
    Projects,
    TokensStoragePath,
    TokensStorageSystemKeyring,
)
from .native_backends_config import BackendConfigurations, native_backends_config
from .paths import PathsBook, app_dirs, ensure_config_file_exists_or_create_it
from .projects_finders import auto_detect_projects


class YouwolEnvironment(BaseModel):
    httpPort: int
    events: Events
    customMiddlewares: List[CustomMiddleware]

    projects: Projects
    commands: Dict[str, Command]

    currentConnection: Connection

    remotes: List[CloudEnvironment]

    pathsBook: PathsBook
    routers: List[FastApiRouter] = []

    backends_configuration: BackendConfigurations

    cache_user: Dict[str, Any] = {}
    cache_py_youwol: Dict[str, Any] = {}

    tokens_storage: TokensStorage

    def reset_databases(self):
        self.backends_configuration.reset_databases()

    def reset_cache(self):
        self.cache_user = {}
        self.cache_py_youwol = {}

    def get_remote_info(self) -> CloudEnvironment:
        env_id = self.currentConnection.envId
        return next(remote for remote in self.remotes if remote.envId == env_id)

    def get_authentication_info(self) -> Authentication:
        remote = self.get_remote_info()
        auth_id = self.currentConnection.authId
        return next(auth for auth in remote.authentications if auth.authId == auth_id)

    def __str__(self):
        def str_middlewares():
            if len(self.customMiddlewares) != 0:
                return f"""
- list of middlewares:
{chr(10).join([f"  * {redirection}" for redirection in self.customMiddlewares])}
"""
            return "- no redirections configured"

        def str_commands():
            if len(self.commands.keys()) != 0:
                return f"""
- list of custom commands:
{chr(10).join([f"  * http://localhost:{self.httpPort}/admin/custom-commands/{cmd}" for cmd in self.commands.keys()])}
"""
            return "- no custom command configured"

        def str_routers():
            if self.routers:
                return f"""
- list of additional routers:
{chr(10).join([f"  * {router.base_path}" for router in self.routers])}
"""
            return "- no custom command configured"

        version = ""
        try:
            version = f"{importlib.metadata.version('youwol')}"
        except importlib.metadata.PackageNotFoundError:
            pass

        return f"""Running with youwol {version}: {youwol}
Configuration loaded from '{self.pathsBook.config}'
- authentication: {self.get_authentication_info()}
- remote : {self.get_remote_info().envId} (on {self.get_remote_info().host})
- paths: {self.pathsBook}
- cdn packages count: {len(self.backends_configuration.cdn_backend.doc_db.data['documents'])}
- assets count: {len(self.backends_configuration.assets_backend.doc_db_asset.data['documents'])}
{str_middlewares()}
{str_commands()}
{str_routers()}
"""


@dataclass(frozen=True)
class FwdArgumentsReload:
    token_storage: Optional[TokensStorage] = None
    remote_connection: Optional[Connection] = None


class YouwolEnvironmentFactory:
    __cached_config: Optional[YouwolEnvironment] = None

    @staticmethod
    async def get():
        cached = YouwolEnvironmentFactory.__cached_config
        config = cached or await YouwolEnvironmentFactory.init()
        return config

    @staticmethod
    async def load_from_file(
        path: Path, fwd_args_reload: Optional[FwdArgumentsReload] = None
    ):
        conf = await safe_load(path=path, fwd_args_reload=fwd_args_reload)
        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        YouwolEnvironmentFactory.__cached_config = conf
        return conf

    @staticmethod
    async def reload(connection: Connection = None):
        cached = YouwolEnvironmentFactory.__cached_config
        conf = await safe_load(
            path=cached.pathsBook.config,
            fwd_args_reload=FwdArgumentsReload(
                remote_connection=connection or cached.currentConnection
            ),
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
            projects=conf.projects,
            commands=conf.commands,
            customMiddlewares=conf.customMiddlewares,
            events=conf.events,
            remotes=conf.remotes,
            backends_configuration=native_backends_config(
                local_http_port=conf.httpPort,
                local_storage=conf.pathsBook.local_storage,
                local_nosql=conf.pathsBook.databases / "docdb",
            ),
            tokens_storage=conf.tokens_storage,
        )
        YouwolEnvironmentFactory.__cached_config = new_conf

    @staticmethod
    async def trigger_on_load(config: YouwolEnvironment):
        context = ContextFactory.get_instance(
            logs_reporters=[InMemoryReporter()],
            data_reporters=[WsDataStreamer()],
            request=None,
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
    path: Path, fwd_args_reload: FwdArgumentsReload = FwdArgumentsReload()
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
            ],
        )

    config: Configuration = await configuration_from_python(path)
    system = config.system
    projects = config.projects
    customization = config.customization
    data_dir = ensure_dir_exists(
        system.localEnvironment.dataDir, root_candidates=app_dirs.user_data_dir
    )
    cache_dir = ensure_dir_exists(
        system.localEnvironment.cacheDir, root_candidates=app_dirs.user_cache_dir
    )

    paths_book = PathsBook(config=path, databases=data_dir, system=cache_dir)

    if not os.access(paths_book.system.parent, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system.parent)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."],
        )
        raise ConfigurationLoadingException(get_status(False))

    if not paths_book.system.exists():
        os.mkdir(paths_book.system)

    check_system_folder_writable.status = True

    if not os.access(paths_book.system, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."],
        )
        raise ConfigurationLoadingException(get_status(False))

    if not paths_book.store_node_modules.exists():
        os.mkdir(paths_book.store_node_modules)

    if not paths_book.packages_cache_path.exists():
        with open(paths_book.packages_cache_path, "w", encoding="UTF-8") as fp:
            json.dump({}, fp)

    if isinstance(projects.finder, (str, Path)):
        #  5/12/2022: Backward compatibility code
        root = projects.finder
        projects.finder = ExplicitProjectsFinder(
            fromPaths=lambda _: auto_detect_projects(
                paths_book=paths_book, root_folder=root
            )
        )

    tokens_storage_conf = config.system.tokensStorage
    if (
        isinstance(tokens_storage_conf, TokensStoragePath)
        or isinstance(tokens_storage_conf, TokensStorageSystemKeyring)
        and not Path(tokens_storage_conf.path).is_absolute()
    ):
        tokens_storage_conf.path = cache_dir / tokens_storage_conf.path

    fwd_args_reload = FwdArgumentsReload(
        token_storage=fwd_args_reload.token_storage
        or await tokens_storage_conf.get_tokens_storage(),
        remote_connection=fwd_args_reload.remote_connection
        or system.cloudEnvironments.defaultConnection,
    )

    return YouwolEnvironment(
        httpPort=system.httpPort,
        routers=customization.endPoints.routers,
        currentConnection=fwd_args_reload.remote_connection,
        events=customization.events,
        pathsBook=paths_book,
        projects=projects,
        commands={c.name: c for c in customization.endPoints.commands},
        customMiddlewares=customization.middlewares,
        remotes=system.cloudEnvironments.environments,
        backends_configuration=native_backends_config(
            local_http_port=system.httpPort,
            local_storage=paths_book.local_storage,
            local_nosql=paths_book.databases / "docdb",
        ),
        tokens_storage=fwd_args_reload.token_storage,
    )


async def get_yw_config_starter(main_args: MainArguments):
    conf_path, _ = ensure_config_file_exists_or_create_it(main_args.config_path)

    return conf_path


def print_invite(conf: YouwolEnvironment, shutdown_script_path: Optional[Path]):
    print(
        f"""{Fore.GREEN}Configuration loaded successfully{Style.RESET_ALL}.
"""
    )
    print(conf)
    msg = cow.milk_random_cow(
        f"""
The desktop application is available at:
http://localhost:{conf.httpPort}/applications/@youwol/platform/latest
The developer portal is available at:
http://localhost:{conf.httpPort}/applications/@youwol/developer-portal/%5E0.1.0
For a Py-YouWol interactive tour:
http://localhost:{conf.httpPort}/applications/@youwol/stories/latest?id=9e664525-1dac-45af-83c6-f4b4ef3866af&mode=reader
"""
    )
    print(msg)
    if shutdown_script_path is not None:
        print()
        print(
            f"Py-youwol will run in background. Use {shutdown_script_path} to stop it :"
        )
        print(f"$ sh {shutdown_script_path}")


api_configuration = ApiConfiguration(open_api_prefix="", base_path="")
