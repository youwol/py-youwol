# standard library
import json
import os

from collections.abc import Awaitable
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Any

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
from youwol.utils.crypto.digest import compute_digest
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
from .models.model_remote import Authentication
from .models.models import ApiConfiguration
from .models.models_config import (
    CloudEnvironment,
    Command,
    Configuration,
    Connection,
    CustomMiddleware,
    Events,
)
from .models.models_features import Features
from .models.models_token_storage import TokensStoragePath, TokensStorageSystemKeyring
from .native_backends_config import BackendConfigurations, native_backends_config
from .paths import PathsBook, app_dirs, ensure_config_file_exists_or_create_it
from .proxied_backends import BackendsStore
from .youwol_environment_models import ProjectsResolver


class YouwolEnvironment(BaseModel):
    """
    Runtime environment of the server.
    """

    httpPort: int
    """
    Serving port,
    defined from the [Configuration](@yw-nav-attr:System.httpPort).
    """

    events: Events
    """
    Plugged events,
    defined from the [Configuration](@yw-nav-attr:Customization.events).
    """

    customMiddlewares: list[CustomMiddleware]
    """
    Custom middlewares,
    defined from the
     [Configuration](@yw-nav-attr:Customization.middlewares).
    """

    projects: ProjectsResolver
    """
    References projects' lookup & creation strategies, defined from the configuration's attribute
    [Configuration.projects](@yw-nav-attr:models.models_config.Configuration.projects).
    """

    commands: dict[str, Command]
    """
    The list of commands,
    defined from the [Configuration](@yw-nav-attr:CustomEndPoints.commands).
    """

    currentConnection: Connection
    """
    The current connection to the remote ecosystem.
    """

    remotes: list[CloudEnvironment]
    """
    The list of available remotes,
    defined from the [Configuration](@yw-nav-attr:System.cloudEnvironments).
    """

    pathsBook: PathsBook

    routers: list[FastApiRouter] = []

    backends_configuration: BackendConfigurations

    cache_user: dict[str, Any] = {}
    cache_py_youwol: dict[str, Any] = {}

    tokens_storage: TokensStorage

    proxied_backends: BackendsStore = BackendsStore()
    """
    The store regarding proxied backends. Proxied backends are usually standalone backend running on their
    own port and proxied by youwol from the base path `/backends/NAME/VERSION/**` (where `NAME` and `VERSION` are
    the name and version of the proxied backend).
    """

    features: Features

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
            version = youwol.__version__
        except ModuleNotFoundError:
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
    token_storage: TokensStorage | None = None
    remote_connection: Connection | None = None
    http_port: int | None = None


class YouwolEnvironmentFactory:
    __cached_config: YouwolEnvironment | None = None
    __cached_config_digest: str | None = None

    @staticmethod
    def __set(cached_config: YouwolEnvironment):
        YouwolEnvironmentFactory.__cached_config = cached_config
        digest = compute_digest(
            cached_config,
            trace_path_root="YouwolEnvFactory__set",
        )
        YouwolEnvironmentFactory.__cached_config_digest = digest.hex()

    @staticmethod
    async def get():
        cached = YouwolEnvironmentFactory.__cached_config
        config = cached or await YouwolEnvironmentFactory.init()
        return config

    @staticmethod
    def get_digest():
        return YouwolEnvironmentFactory.__cached_config_digest

    @staticmethod
    async def load_from_file(
        path: Path, fwd_args_reload: FwdArgumentsReload | None = None
    ):
        cached = YouwolEnvironmentFactory.__cached_config
        if fwd_args_reload.http_port and fwd_args_reload.http_port != cached.httpPort:
            raise ValueError(
                "Can not `load_from_file` a Configuration that changes the serving HTTP port."
            )

        fwd_args_reload = FwdArgumentsReload(
            token_storage=fwd_args_reload.token_storage,
            remote_connection=fwd_args_reload.remote_connection,
            http_port=cached.httpPort,
        )
        conf = await safe_load(path=path, fwd_args_reload=fwd_args_reload)
        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        YouwolEnvironmentFactory.__set(conf)
        return conf

    @staticmethod
    async def reload(connection: Connection | None = None):
        cached = YouwolEnvironmentFactory.__cached_config
        conf = await safe_load(
            path=cached.pathsBook.config,
            fwd_args_reload=FwdArgumentsReload(
                remote_connection=connection or cached.currentConnection,
                http_port=cached.httpPort,
            ),
        )

        await YouwolEnvironmentFactory.trigger_on_load(config=conf)
        YouwolEnvironmentFactory.__set(conf)
        return conf

    @staticmethod
    async def init():
        path = await get_yw_config_starter(get_main_arguments())
        conf = await safe_load(path=path)

        YouwolEnvironmentFactory.__set(conf)
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
        YouwolEnvironmentFactory.__set(new_conf)

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
    """
    Return the current environment, used in particular to inject it in FastAPI registered end-points.

    Return:
        Current environment
    """
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
    config_projects = config.projects
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
        http_port=fwd_args_reload.http_port or system.httpPort,
    )

    return YouwolEnvironment(
        httpPort=fwd_args_reload.http_port,
        routers=customization.endPoints.routers,
        currentConnection=fwd_args_reload.remote_connection,
        events=customization.events,
        pathsBook=paths_book,
        projects=ProjectsResolver.from_configuration(config_projects=config_projects),
        commands={c.name: c for c in customization.endPoints.commands},
        customMiddlewares=customization.middlewares,
        remotes=system.cloudEnvironments.environments,
        backends_configuration=native_backends_config(
            local_http_port=system.httpPort,
            local_storage=paths_book.local_storage,
            local_nosql=paths_book.databases / "docdb",
        ),
        tokens_storage=fwd_args_reload.token_storage,
        features=config.features,
    )


async def get_yw_config_starter(main_args: MainArguments):
    conf_path, _ = ensure_config_file_exists_or_create_it(main_args.config_path)

    return conf_path


def print_invite(conf: YouwolEnvironment, shutdown_script_path: Path | None):
    print(
        f"""{Fore.GREEN}Configuration loaded successfully{Style.RESET_ALL}.
"""
    )
    print(conf)
    msg = cow.milk_random_cow(
        f"""
The desktop application is available at:
http://localhost:{conf.httpPort}/applications/@youwol/platform/latest
Regarding Py-YouWol documentation:
http://localhost:{conf.httpPort}/doc
"""
    )
    print(msg)
    if shutdown_script_path is not None:
        print()
        print(
            f"Py-youwol will run in background. Use {shutdown_script_path} to stop it :"
        )
        print(f"$ sh {shutdown_script_path}")


api_configuration: ApiConfiguration = ApiConfiguration(open_api_prefix="", base_path="")
"""
The environment's API configuration.
"""
