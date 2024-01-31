# standard library
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from pathlib import Path

# typing
from typing import Any, Callable, Optional, Union

# third parties
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment.models.defaults import (
    default_auth_provider,
    default_http_port,
    default_ignored_paths,
    default_path_cache_dir,
    default_path_data_dir,
    default_path_projects_dir,
    default_path_tokens_storage,
    default_path_tokens_storage_encrypted,
    default_platform_host,
)
from youwol.app.environment.models.models import (
    ConfigPath,
    OnProjectsCountUpdate,
    ProjectsFinderHandler,
)
from youwol.app.environment.models.projects_finder_handlers import (
    ExplicitProjectsFinderHandler,
    RecursiveProjectFinderHandler,
)
from youwol.app.environment.paths import PathsBook

# Youwol utilities
from youwol.utils import JSON, Context
from youwol.utils.clients.oidc.oidc_config import PrivateClient, PublicClient
from youwol.utils.clients.oidc.tokens_manager import TokensStorageCache
from youwol.utils.context import ContextFactory
from youwol.utils.servers.fast_api import FastApiRouter

# relative
from .tokens_storage.encrypted_file import AlgoSpec, TokensStorageKeyring
from .tokens_storage.file import TokensStorageFile


class Events(BaseModel):
    """
    Gather the list of events on which user actions can be performed.
    """

    onLoad: Callable[[Context], Optional[Union[Any, Awaitable[Any]]]] = None
    """
    Event triggered when the configuration is loaded.
    """


class UploadTarget(BaseModel):
    """
    Upload target are used when configuring Pipeline, see dedicated documentation of the pipeline.
    Pipelines can define some required upload targets by sub-classing this class.
    """

    name: str
    """
    Name of the upload target.
    """


class UploadTargets(BaseModel):
    """
    Upload targets are used when configuring Pipeline, see dedicated documentation of the pipeline.
    """

    targets: list[UploadTarget]
    """
    Gather `UploadTarget` targets of similar king (e.g. multiple docker registries, multiple remote CDN )
    """


class ProjectTemplate(BaseModel):
    """
    Definition of a template that create an initial project folder that can be built & published.

    In most practical cases, project template generator are exposed by python packages and consumed in the configuration
    file, for instance regarding the typescript pipeline of youwol:

    ```python hl_lines="5 11"
    from youwol.app.environment import (
        Configuration,
        Projects,
    )
    from youwol.pipelines.pipeline_typescript_weback_npm import app_ts_webpack_template

    projects_folder = Path.home() / 'destination'

    Configuration(
        projects=Projects(
            templates=[app_ts_webpack_template(folder=projects_folder)],
        )
    )
    ```

    """

    icon: Any
    """
    A json DOM representation of the icon for the template. See the library '@youwol/rx-vdom'.
    """

    type: str
    """
    A unique type id that represents the type of the project.
    """

    folder: Union[str, Path]
    """
    Where the created project folders will be located.
    """

    parameters: dict[str, str]
    """
    A dictionary *'parameter name'* -> *'parameter default value'* defining the parameters the user will have to supply
    to create the template.
    """

    generator: Callable[[Path, dict[str, str], Context], Awaitable[tuple[str, Path]]]
    """
    The generator called to create the template project, arguments are:

    1 - First argument is the folder's path in which the project needs to be created (parent folder
        of the created project).

    2 - Second argument is the value of the parameters the user supplied.

    3 - Third argument is the context.

    Return the project's name and its path.
    """


class ProjectsFinder(BaseModel):
    """
    Abstract class for ProjectsFinder.

    Derived classes need to implement the **'handler'** method.

    See [RecursiveProjectsFinder](@yw-nav-class:youwol.app.environment.models.models_config.RecursiveProjectsFinder) and
    [ExplicitProjectsFinder](@yw-nav-class:youwol.app.environment.models.models_config.ExplicitProjectsFinder).
    """

    def handler(
        self, paths_book: PathsBook, on_projects_count_update: OnProjectsCountUpdate
    ) -> ProjectsFinderHandler:
        raise NotImplementedError()


class RecursiveProjectsFinder(ProjectsFinder):
    """
    Strategy to discover all projects below the provided paths with optional continuous watching.

    Example:
        ```python hl_lines="6 13-17"
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                Projects,
                RecursiveProjectsFinder
            )

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=RecursiveProjectsFinder(
                    fromPaths=[projects_folder],
                    ignoredPatterns=["**/dist", "**/node_modules", "**/.template"],
                    watch=True
                )
            )
        )
        ```

    **Troubleshooting**

    Inotify uses a system-wide limit called `max_user_watches`, which determines the maximum number of files or
    directories that a user can watch at any given time. This limit is set by the system administrator
    and is typically set to a low value such as `8192` or `16384`.
    When the limit is reached, inotify will stop working and will not be able to watch for changes
    in any additional files or directories. A common displayed error in such case is:
    ```bash
    Failed to watch /var/log/messages; upper limit on inotify watches reached!
    Please increase the amount of inotify watches allowed per user via '/proc/sys/fs/inotify/max_user_watches'.`
    ```

    To increase the limit, you can edit the `sysctl.conf` file and add a line to increase the `max_user_watches` limit.
    For example:
    ```bash
    echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
    ```
    Then run

    ```bash
    sudo sysctl -p
    ```
    This will increase the max_user_watches limit to the new value.

    Note that this change will not take effect until the system is rebooted.
    You may also check the current value of the limit by running

    ```bash
    cat /proc/sys/fs/inotify/max_user_watches
    ```

    The value `524288` is a commonly used value for increasing the max_user_watches limit because it's a reasonably
     large number that should be sufficient for most use cases.
    It allows a user to watch up to `524288` files or directories at any given time.
    This value is typically high enough to handle most use cases and should be enough to prevent inotify from
    reaching its limit and stop working.
    """

    fromPaths: list[ConfigPath] = [Path.home() / default_path_projects_dir]
    """
    All projects below these paths will be discovered.

    By default uses
    [default_path_projects_dir](@yw-nav-glob:youwol.app.environment.models.defaults.default_path_projects_dir).
    """

    ignoredPatterns: list[str] = default_ignored_paths
    """
    List of ignored patterns to discard folder when traversing the tree.

    By default uses [default_ignored_paths](@yw-nav-glob:youwol.app.environment.models.defaults.default_ignored_paths).

    See [fnmatch](https://docs.python.org/3/library/fnmatch.html) regarding the patterns specification.
    """
    watch: bool = True
    """
    Whether or not watching added/removed projects is activated.
    """

    def handler(
        self, paths_book: PathsBook, on_projects_count_update: OnProjectsCountUpdate
    ):
        return RecursiveProjectFinderHandler(
            paths=self.fromPaths,
            ignored_patterns=self.ignoredPatterns,
            paths_book=paths_book,
            on_projects_count_update=on_projects_count_update,
        )


class ExplicitProjectsFinder(ProjectsFinder):
    """
    Strategy to discover all projects directly below some provided paths.

     > ⚠️ Changes in directories content is not watched: projects added/removed from provided paths do not trigger
     updates.
     The [RecursiveProjectsFinder](@yw-nav-class:youwol.app.environment.models.models_config.RecursiveProjectsFinder)
     class allows such features.

     Example:
        ```python hl_lines="6 13-15"
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                Projects,
                ExplicitProjectsFinder
            )

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=ExplicitProjectsFinder(
                    fromPaths=[projects_folder]
                )
            )
        )
        ```

    """

    fromPaths: Union[list[ConfigPath], Callable[[PathsBook], list[ConfigPath]]]
    """
    The paths in which to look for projects as direct children.

    Can be provided as a function that gets the [PathsBook](@yw-nav-class:youwol.app.environment.paths.PathsBook)
    instance - useful when looking for folder's location depending on some typical paths of youwol.
    """

    def handler(
        self, paths_book: PathsBook, on_projects_count_update: OnProjectsCountUpdate
    ):
        return ExplicitProjectsFinderHandler(
            paths=self.fromPaths,
            paths_book=paths_book,
            on_projects_count_update=on_projects_count_update,
        )


class Projects(BaseModel):
    """
    It essentially defines the projects a user is working on, including:

    *  a strategy to locate them from the local disk.
    *  some references on `template` objects that allows to create an initial draft of a project for a particular stack

    Example:
        A typical example of this section of the configuration looks like:

        ```python hl_lines="5 6 8 13 14 15 16 17 18"
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                Projects,
                RecursiveProjectsFinder
            )
        from youwol.pipelines.pipeline_typescript_weback_npm import app_ts_webpack_template

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=RecursiveProjectsFinder(
                    fromPaths=[projects_folder],
                ),
                templates=[app_ts_webpack_template(folder=projects_folder)],
            )
        )
        ```
    """

    finder: Union[ProjectsFinder, ConfigPath] = RecursiveProjectsFinder()
    """
    Strategy for finding projects, most of the times the
    [RecursiveProjectsFinder](@yw-nav-class:youwol.app.environment.models.models_config.RecursiveProjectsFinder)
    strategy is employed.
    The less employed
    [ExplicitProjectsFinder](@yw-nav-class:youwol.app.environment.models.models_config.ExplicitProjectsFinder)
    can also be used.
    """

    templates: list[ProjectTemplate] = []
    """
    List of projects' template: they are essentially generators that create an initial project structure for a
     particular stack.
    """


class AuthorizationProvider(BaseModel):
    """
    Authorization provider.
    """

    openidBaseUrl: str
    """
    OpenId base URL.
    """

    openidClient: Union[PrivateClient, PublicClient]
    """
    openId client.
    """

    keycloakAdminBaseUrl: Optional[str] = None
    keycloakAdminClient: Optional[PrivateClient] = None


class Authentication(BaseModel):
    """
    Virtual base class for authentication modes.

    See
    [BrowserAuth](@yw-nav-class:youwol.app.environment.models.models_config.BrowserAuth) or
    [DirectAuth](@yw-nav-class:youwol.app.environment.models.models_config.DirectAuth)
    """

    authId: str
    """
    Unique id of the authentication for encapsulating in
    [CloudEnvironment](@yw-nav-class:youwol.app.environment.models.models_config.CloudEnvironment).
    """


class BrowserAuth(Authentication):
    """
    Authentication using the browser with cookies: the browser automatically handle authentication (eventually
    redirecting to the login page if needed).
    """


class DirectAuth(Authentication):
    """
    Authentication using direct-flow.
    """

    userName: str
    """
    Credential's user-name.
    """

    password: str
    """
    Credential's password.
    """


class CloudEnvironment(BaseModel):
    """
    Specification of a remote YouWol environment.

    Example:
        The standard youwol cloud environment connected using a browser connection or a direct connection:

        ```python
        from pathlib import Path

        from youwol.app.environment import (
            Configuration,
            System,
            CloudEnvironments,
            DirectAuth,
            BrowserAuth,
            CloudEnvironment,
            get_standard_auth_provider,
        )

        environment = CloudEnvironment(
            envId="youwol",
            host="platform.youwol.com",
            authProvider=get_standard_auth_provider("platform.youwol.com"),
            authentications=[
                BrowserAuth(authId="browser"),
                DirectAuth(authId="bar", userName="bar", password="bar-pwd"),
            ],
        )
        ```
    """

    envId: str
    """
    Unique id for this environment.
    """

    host: str
    """
    Host of the environment (e.g. `platform.youwol.com`).
    """

    authProvider: AuthorizationProvider
    """
    Specification of the authorization provider.

    For a Keycloak authentication provider including a properly configured `youwol` realm, the function
     [default_auth_provider](@yw-nav-func:youwol.app.environment.models.defaults.default_auth_provider) is available.
    """

    authentications: list[Authentication]
    """
    List of accepted authentications for the environment.
    """


class Connection(BaseModel):
    """
    A connection is the association of an environment id and an authentication id.
    """

    envId: str
    """
    Reference an environment ID provided in
     [CloudEnvironments](@yw-nav-attr:youwol.app.environment.models.models_config.CloudEnvironments.environments).
    """

    authId: str
    """
    Reference an authentication ID provided in the
     [CloudEnvironment](@yw-nav-class:youwol.app.environment.models.models_config.CloudEnvironment) with ID `envId`.
    """


class CloudEnvironments(BaseModel):
    """
    Cloud environments on which connection can be established.

    At a particular time, py-youwol is connected to one cloud environment.
    This is where missing assets (data, libraries, backends) are retrieved.

    Example:
        Below is an example declaring 2 cloud environments, one related to a hypothetical remote environment of
        a company `foo`, and the second the regular youwol remote environment :
        ```python

        from pathlib import Path

        from youwol.app.environment import (
            Configuration,
            System,
            CloudEnvironments,
            LocalEnvironment,
            DirectAuth,
            BrowserAuth,
            CloudEnvironment,
            get_standard_auth_provider,
            Connection,
            get_standard_youwol_env,
        )

        company_name = "foo"
        foo_cloud = CloudEnvironment(
            envId=company_name,
            host=f"platform.{company_name}.com",
            authProvider=get_standard_auth_provider(f"platform.{company_name}.com"),
            authentications=[
                BrowserAuth(authId="browser"),
                DirectAuth(authId="bar", userName="bar", password="bar-pwd"),
            ]
        )


        Configuration(
            system=System(
                cloudEnvironments=CloudEnvironments(
                    defaultConnection=Connection(envId=company_name, authId="bar"),
                    environments=[
                        foo_cloud,
                        get_standard_youwol_env(env_id="public-youwol"),
                    ],
                )
            )
        )
        ```
    """

    defaultConnection: Connection
    """
    Connection used when py-youwol is started.

    To switch connection after youwol has started, see end-point
     [Login](@yw-nav-func:youwol.app.routers.environment.router.login).
    """

    environments: list[CloudEnvironment]
    """
    Available (YouWol) cloud environments with which youwol can connect.
    """


class LocalEnvironment(BaseModel):
    """
    Path of folders on disk to store data.
    If paths are relatives, they are referenced with respect to the parent folder of the configuration file.

    Example:
        ```python
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                System,
                LocalEnvironment
            )

        Configuration(
            system=System(
                localEnvironment=LocalEnvironment(
                    dataDir=Path.home() / 'youwol' / 'data',
                    cacheDir=Path.home() / 'youwol' / 'cache'
                )
            )
        )
        ```

    """

    dataDir: ConfigPath = default_path_data_dir
    """
    Defines folder location in which persisted data are saved.

    See [default_path_data_dir](@yw-nav-glob:youwol.app.environment.models.defaults.default_path_data_dir)
     regarding default value.
    value.
    """

    cacheDir: ConfigPath = default_path_cache_dir
    """
    Defines folder location of cached data.

    See [default_path_cache_dir](@yw-nav-glob:youwol.app.environment.models.defaults.default_path_cache_dir)
     regarding default value.
    """


class TokensStorageConf(ABC):
    """
    Abstract class for tokens storage.
    """

    @abstractmethod
    async def get_tokens_storage(self):
        pass


class TokensStorageSystemKeyring(TokensStorageConf, BaseModel):
    """
    Tokens storage using system's keyring.
    """

    path: Optional[Union[str, Path]] = default_path_tokens_storage_encrypted
    """
    The path of the system keyring encrypted file.

    See <a href="@yw-nav-glob:youwol.app.environment.models.defaults.default_path_tokens_storage_encrypted">
    default_path_tokens_storage_encrypted</a>
    regarding default value.
    """

    service: str = "py-youwol"
    """
    Service name.
    """

    algo: AlgoSpec = "any"
    """
    Algorithm used for encryption.
    """

    async def get_tokens_storage(self):
        path = self.path if isinstance(self.path, Path) else Path(self.path)
        result = TokensStorageKeyring(
            service=self.service, absolute_path=path, algo=self.algo
        )
        await result.load_data()
        return result


class TokensStoragePath(TokensStorageConf, BaseModel):
    """
    Tokens storage using a TokensStorageFile.
    """

    path: Optional[Union[str, Path]] = default_path_tokens_storage
    """
    Path where the file is saved on disk.

    See [default_path_tokens_storage](@yw-nav-glob:youwol.app.environment.models.defaults.default_path_tokens_storage)
     regarding default value.
    """

    async def get_tokens_storage(self):
        path = self.path if isinstance(self.path, Path) else Path(self.path)
        result = TokensStorageFile(path)
        await result.load_data()
        return result


class TokensStorageInMemory(TokensStorageConf):
    """
    In memory tokens storage.
    """

    async def get_tokens_storage(self):
        return TokensStorageCache(cache=ContextFactory.with_static_data["auth_cache"])


class System(BaseModel):
    """
    Gathers the configuration options related to downloading and storing assets in the local disk.

    The default value is most of the time adapted for most users:

    ```python hl_lines="5 9"
    from pathlib import Path

    from youwol.app.environment import (
            Configuration,
            System
        )

    Configuration(
        system=System()
    )
    ```
    In a nutshell:

    *  it defines the serving http port to `2000`
    *  it connects to `platform.youwol.com` to download missing assets, using a browser based authentication
    (through cookies)
    *  it persists the assets in a common place on your computer
    (see [LocalEnvironment](@yw-nav-class:youwol.app.environment.models.models_config.LocalEnvironment))

    The above example is equivalent to:
    ```python
    from pathlib import Path

    from youwol.app.environment import (
            Configuration,
            System,
            TokensStorageSystemKeyring,
            CloudEnvironments,
            CloudEnvironment,
            Connection,
            AuthorizationProvider,
            BrowserAuth,
            LocalEnvironment
        )

    Configuration(
        system=System(
            httpPort=2000,
            tokensStorage=TokensStorageSystemKeyring(),
            cloudEnvironments=CloudEnvironments(
                defaultConnection=Connection(
                    envId="remote", authId="browser"
                ),
                environments=[
                    CloudEnvironment(
                        envId="remote",
                        host=default_platform_host,
                        authProvider=AuthorizationProvider(
                            **default_auth_provider()
                        ),
                        authentications=[BrowserAuth(authId="browser")],
                    )
                ],
            ),
            localEnvironment=LocalEnvironment()
        )
    )
    ```
    """

    httpPort: Optional[int] = default_http_port
    """
    Local port on which py-youwol is served.
    It may be overriden using command line argument `--port` when starting youwol.
    """

    tokensStorage: Optional[TokensStorageConf] = TokensStorageSystemKeyring()
    """
    How to store JWT tokens:

    * <a href="@yw-nav-class:youwol.app.environment.models.models_config.TokensStorageSystemKeyring">
     TokensStorageSystemKeyring()</a>:
    use system keyring
    * [TokensStoragePath()](@yw-nav-class:youwol.app.environment.models.models_config.TokensStoragePath) :
     store in file
    * [TokensStorageInMemory()](@yw-nav-class:youwol.app.environment.models.models_config.TokensStorageInMemory) :
     store in memory
    """

    cloudEnvironments: CloudEnvironments = CloudEnvironments(
        defaultConnection=Connection(envId="remote", authId="browser"),
        environments=[
            CloudEnvironment(
                envId="remote",
                host=default_platform_host,
                authProvider=AuthorizationProvider(**default_auth_provider()),
                authentications=[BrowserAuth(authId="browser")],
            )
        ],
    )
    """
    Specify remote environment(s) from where data can be collected.
    """

    localEnvironment: LocalEnvironment = LocalEnvironment()
    """
    Specify how data are persisted in the computer.
    """


class Command(BaseModel):
    """
    Defines commands that can be triggered using HTTP call. They are served from
    `/admin/custom-commands/$NAME`, where `$NAME` is the name of the command.

    Example:
        ```python hl_lines="4 12-19"
        from youwol.app.environment import (
            Configuration,
            Customization,
            Command,
            CustomEndPoints,
        )

        Configuration(
            customization=Customization(
                endPoints=CustomEndPoints(
                    commands=[
                        Command(
                            name="example",
                            do_get=lambda ctx: ctx.info(text="GET:example")
                        ),
                        Command(
                            name="example",
                            do_post=lambda body, ctx: ctx.info(text="POST:example"),
                        )
                    ]
                )
            )
        )
        ```
        In the above example, two commands (one `GET` and one `POST`) are defined,
         both exposed from `/admin/custom-commands/example`.
    """

    name: str
    """
    Name of the command.
    """

    do_get: Optional[Callable[[Context], Union[Awaitable[JSON], JSON]]] = None
    """
    The function to trigger on `GET`.
    """

    do_post: Optional[Callable[[JSON, Context], Union[Awaitable[JSON], JSON]]] = None
    """
    The function to trigger on `POST`, the first argument of the callable is the JSON body of the command.
    """

    do_put: Optional[Callable[[JSON, Context], Union[Awaitable[JSON], JSON]]] = None
    """
    The function to trigger on `PUT`, the first argument of the callable is the JSON body of the command.
    """

    do_delete: Optional[Callable[[Context], Union[Awaitable[JSON], JSON]]] = None
    """
    The function to trigger on `DELETE`.
    """


class CustomEndPoints(BaseModel):
    """
    Extends the server by adding custom end-points.
    """

    commands: Optional[list[Command]] = []
    """
    A list of commands that can be triggered via HTTP requests.
    """

    routers: Optional[list[FastApiRouter]] = []
    """
    Additional routers to bind to the environment.
    """


class CustomMiddleware(BaseModel, ABC):
    """
    Abstract class to define middleware, see for instance the
    [FlowSwitcherMiddleware](@yw-nav-class:youwol.app.environment.models.models_config.FlowSwitcherMiddleware).

    Derived implementation must provide the **dispatch** method.

    Example:
        Below is a typical example
        ```python
        from starlette.middleware.base import RequestResponseEndpoint
        from starlette.requests import Request
        from youwol.app.environment import (
            CustomMiddleware
        )

        class HelloMiddleware(CustomMiddleware):

            async def dispatch(
                self,
                incoming_request: Request,
                call_next: RequestResponseEndpoint,
                context: Context,
            ):
                async with context.start(
                    action="HelloMiddleware.dispatch", with_labels=[Label.MIDDLEWARE]
                ) as ctx:
                    await ctx.info("Hello")
                    return await call_next(incoming_request)
        ```
    """

    async def dispatch(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
        """
        Virtual method to implement by derived class.

        Attributes:
            incoming_request: incoming [Request](https://fastapi.tiangolo.com/reference/request/)
            call_next: trigger the next target in the call stack
            context: [Context](@yw-nav-class:youwol.utils.context.Context)

        Return:
            The response
        """
        raise NotImplementedError("CustomMiddleware.switch not implemented")


class Customization(BaseModel):
    """
    Exposes customization of the server, *e.g.* :

    *  Adding custom end points to the server
    *  Adding custom middlewares
    *  React to events

    Example:
        Below is an example spanning most of the attribute of the class:

        ```python
        from youwol.app.environment import (
            Configuration,
            Customization,
            Command,
            CustomEndPoints,
            CustomMiddleware
        )

        class HelloMiddleware(CustomMiddleware):
            name = "HelloMiddleware"

            async def dispatch(
                self,
                incoming_request: Request,
                call_next: RequestResponseEndpoint,
                context: Context,
            ):
                async with context.start(
                    action="HelloMiddleware.dispatch", with_labels=[Label.MIDDLEWARE]
                ) as ctx:  # type: Context
                    await ctx.info("Hello")
                    return await call_next(incoming_request)



        Configuration(
            customization=Customization(
                events=Events(onLoad=lambda ctx: ctx.info("Configuration loaded")),
                middlewares=[
                    # Middlewares will be accessed in the order specified by this list
                    HelloMiddleware()
                ],
                endPoints=CustomEndPoints(
                    commands=[
                        Command(
                            name="example",
                            do_get=lambda ctx: ctx.info(text="GET:example")
                        ),
                        Command(
                            name="example",
                            do_post=lambda body, ctx: ctx.info(text="POST:example"),
                        )
                    ]
                )
            )
        )
        ```

        In a nutshell:

        *  **events**: allows to react to some events, here the `onLoad` event (configuration loaded).
        *  **middlewares**: attribute provide the ability to plug custom middlewares.
        *  **endPoints**: attribute allows to add end-points to the youwol server, usually as
        [Command](@yw-nav-class:youwol.app.environment.models.models_config.Command).

    """

    endPoints: CustomEndPoints = CustomEndPoints()
    """
    Allows adding custom end-points to the environment.
    """

    middlewares: Optional[list[CustomMiddleware]] = []
    """
    Allows adding custom end-points to the environment.
    """
    events: Optional[Events] = Events()
    """
    Allows adding custom end-points to the environment.
    """


class Configuration(BaseModel):
    """
    Defines py-youwol running environment.

    Every parameter is optional, to provide the default configuration:

    ```python

    from youwol.app.environment import Configuration

    Configuration()
    ```

    Which is equivalent to:
    ```python

    from youwol.app.environment import Configuration, System, Projects, Customization

    Configuration(
        system=System(),
        projects=Projects(),
        customization=Customization()
    )
    ```
    """

    system: System = System()
    """
    Essentially about data and authorization:

    *  from which remote environment missing assets are downloaded
    *  how to authenticate
    *  where to store the assets on the local disk
    *  *etc*
    """

    projects: Projects = Projects()
    """
    Related to the projects the user is working on (*e.g.* libraries, applications, backends).
    """

    customization: Customization = Customization()
    """
    Various handles for customization (*e.g.* middleware, commands, ...)
    """
