# standard library
from abc import ABC
from collections.abc import Awaitable, Callable

# typing
from typing import Any

# third parties
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment.models.defaults import (
    default_auth_provider,
    default_http_port,
    default_path_cache_dir,
    default_path_data_dir,
    default_platform_host,
)
from youwol.app.environment.models.models import ConfigPath

# Youwol utilities
from youwol.utils import JSON, Context
from youwol.utils.clients.oidc.oidc_config import PrivateClient, PublicClient
from youwol.utils.servers.fast_api import FastApiRouter

# relative
from .models_project import Projects
from .models_token_storage import TokensStorageConf, TokensStorageSystemKeyring


class Events(BaseModel):
    """
    Gather the list of events on which user actions can be performed.
    """

    onLoad: Callable[[Context], Any | Awaitable[Any] | None] = None
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


class AuthorizationProvider(BaseModel):
    """
    Authorization provider.
    """

    openidBaseUrl: str
    """
    OpenId base URL.
    """

    openidClient: PrivateClient | PublicClient
    """
    openId client.
    """

    keycloakAdminBaseUrl: str | None = None
    keycloakAdminClient: PrivateClient | None = None


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

    httpPort: int | None = default_http_port
    """
    Local port on which py-youwol is served.
    It may be overriden using command line argument `--port` when starting youwol.
    """

    tokensStorage: TokensStorageConf | None = TokensStorageSystemKeyring()
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

    do_get: Callable[[Context], Awaitable[JSON] | JSON] | None = None
    """
    The function to trigger on `GET`.
    """

    do_post: Callable[[JSON, Context], Awaitable[JSON] | JSON] | None = None
    """
    The function to trigger on `POST`, the first argument of the callable is the JSON body of the command.
    """

    do_put: Callable[[JSON, Context], Awaitable[JSON] | JSON] | None = None
    """
    The function to trigger on `PUT`, the first argument of the callable is the JSON body of the command.
    """

    do_delete: Callable[[Context], Awaitable[JSON] | JSON] | None = None
    """
    The function to trigger on `DELETE`.
    """


class CustomEndPoints(BaseModel):
    """
    Extends the server by adding custom end-points.
    """

    commands: list[Command] | None = []
    """
    A list of commands that can be triggered via HTTP requests.
    """

    routers: list[FastApiRouter] | None = []
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
    ) -> Response | None:
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

    middlewares: list[CustomMiddleware] | None = []
    """
    Allows adding custom end-points to the environment.
    """
    events: Events | None = Events()
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
