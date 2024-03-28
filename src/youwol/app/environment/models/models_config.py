"""
This file gathers top level [configuration](@yw-nav-class:models_config.Configuration)'s models.
"""

# future
from __future__ import annotations

# standard library
import tempfile

from abc import ABC
from collections.abc import Awaitable, Callable
from pathlib import Path

# typing
from typing import Any, Literal

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
from youwol.utils.servers.fast_api import FastApiRouter

# relative
from .model_remote import (
    AuthorizationProvider,
    BrowserAuth,
    CloudEnvironment,
    CloudEnvironments,
    Connection,
)
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


class LocalEnvironment(BaseModel):
    """
    Path of folders on disk to store data.
    If paths are relatives, they are referenced with respect to the parent folder of the configuration file.

    Example:
        <code-snippet language='python'>
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
        </code-snippet>
    """

    dataDir: ConfigPath = default_path_data_dir
    """
    Defines folder location in which persisted data are saved.

    See [default_path_data_dir](@yw-nav-glob:default_path_data_dir)
     regarding default value.
    value.
    """

    cacheDir: ConfigPath = default_path_cache_dir
    """
    Defines folder location of cached data.

    See [default_path_cache_dir](@yw-nav-glob:default_path_cache_dir)
     regarding default value.
    """


class BrowserCache(BaseModel):
    """
    Represents the simulated browser cache within YouWol, which is exclusively activated for `GET` requests initiated
    by a browser.

    Rationale:
        Browser caching can circumvent certain side effects triggered during resource requests.
        For instance, when requesting a missing resource, the server downloads it into the local database if it's
        not already available. However, when transitioning from one configuration (e.g., `A`) to another (e.g., `B`),
        a resource that was available in `A` but not in `B`, and is cached by the browser, won't be downloaded
        when transitioning to `B`. Instead, it will be served from the cache, thereby bypassing the associated
        side effects, such as the download process. Due to this behavior and a lack of configurability,
        an explicit emulation of a browser cache has been incorporated into YouWol.

    Details:
        The cache is only populated by responses that include a header specified by
        [YouwolHeaders.yw_browser_cache_directive](@yw-nav-attr:YouwolHeaders.yw_browser_cache_directive),
        which is an opt-in feature from the backends that create the response.

        Persisted cached elements (if `mode=='disk'`) are gathered in files on the user disk:
        *  the folder location is defined by the attribute `cachesFolder`.
        *  their name represents the caching key for the session, combination of:
            *  user-provided `key` function (representing an ID relative to the YouWol configuration)
            *  user information automatically injected by the YouWol implementation.
        *  the entries included do not copy the responses' content, rather, they reference the path on the disk of
        the corresponding files.

        Regardless of the `mode`, a match for a response is retrieved if both:
        *  the caching key for the session match
        *  the target URL match

        When a response is cached, any associated `Cache-Control` header is replaced by `no-cache, no-store`.

        Implementation details can be found in the [BrowserCacheStore](@yw-nav-class:BrowserCacheStore) documentation.

    Note:
        By default, the configuration part of the key is the path of the local database, which should suffice for
        most use cases and allows sharing the cache for configurations that share the same local database.

        For scenario where elements of the configuration re-route some incoming requests out of their normal
        destination, it may be necessary to adjust the attributes [key](@yw-nav-attr:BrowserCache.key) and/or
        [ignore](@yw-nav-attr:BrowserCache.ignore).

    Warning:
        If the [key](@yw-nav-attr:BrowserCache.key) attribute reference the local database (which definitely should),
        manual changes within the local database introduce potentials un-synchronization
        with the persisted caching files. It can lead to resources being fetched from the cache while not existing
        in the local databases (preventing *e.g.* their download).
    """

    key: Callable[[Configuration], Any] = (
        lambda conf: conf.system.localEnvironment.dataDir
    )
    """
    A callable that takes a `Configuration` object as input and returns an object identifying the configuration
    part of the session caching key.

    Example:
        For a key specific to the whole configuration, you can provide:

        <code-snippet>
        cache = BrowserCache(key=lambda conf: conf)
        </code-snippet>
    """

    mode: Literal["in-memory", "disk"] = "disk"
    """
    The mode of the cache, either `in-memory` or `disk`. If `in-memory` is used, the cache is always empty when YouWol
    start.
    """

    maxCount: int = 1000
    """
    Approximate maximum items count in the persisted file (the max-count is ensured only when YouWol start).
    """

    cachesFolder: ConfigPath = Path(tempfile.gettempdir()) / "yw" / "browser-caches"
    """
    Folder used to store caching files on disk.
    """

    ignore: Callable[[Request, Configuration, Context], bool | Awaitable[bool]] = (
        lambda _req, _resp, _ctx: False
    )
    """
    If provided, the caching layer is ignored for the incoming request using the current configuration if the function
    returns `True`.

    Example:
        It can be employed to disregard any routes aligning with a [CdnSwitch](@yw-nav-class:CdnSwitch) in
        the configuration, if a corresponding dev-server is active.
        However, it's worth noting that dev-servers should operate using a 'work-in-progress' version
        (denoted by a suffix `-wip`), ensuring that caching is disabled, allowing the default configuration
        to function smoothly.
    """

    disable_write: Callable[
        [Request, Response, Configuration, Context], bool | Awaitable[bool]
    ] = lambda _req, _resp, _conf, _ctx: False
    """
    Similar to `ignore`, except that it only disable writing within the cache. It is useful when decision regarding
    caching can not be acted before the response have been retrieved.

    Example:
        It can be employed to disregard caching when a middleware has intercepted a request and modified the response
        from the original one. A typical example can be a middleware applying brotli decompression:

    <code-snippet language="python">
    class BrotliDecompressMiddleware(CustomMiddleware):
        async def dispatch(
            self,
            incoming_request: Request,
            call_next: RequestResponseEndpoint,
            context: Context,
        ):
            async with context.start(
                action="BrotliDecompressMiddleware.dispatch", with_labels=[Label.MIDDLEWARE]
            ) as ctx:  # type: Context
                response = await call_next(incoming_request)
                if response.headers.get("content-encoding") != "br":
                    return response

                binary = b""
                async for data in response.body_iterator:
                    binary += data
                decompressed = brotli.decompress(binary)
                headers = {
                    **response.headers,
                    "content-length": str(len(decompressed)),
                    "content-encoding": "identity",
                    "do-not-cache": "true"
                }
                resp = Response(decompressed.decode("utf8"), headers=headers)
                return resp

    Configuration(
        system=System(
            browserEnvironment=BrowserEnvironment(
                cache=BrowserCache(
                    disable_write = lambda _, resp, _, _: "do-not-cache" in resp.headers
                )
            )
        ),
    </code-snippet>

    """


class BrowserEnvironment(BaseModel):
    """
    Collects configuration options related to the browser.

    This class is associated with the [BrowserMiddleware](@yw-nav-class:BrowserMiddleware),
    which is one of the initial middlewares intercepting incoming requests in the YouWol server.
    """

    cache: BrowserCache = BrowserCache()
    """
    Represents the emulated browser cache within YouWol.
    """
    onEnter: Callable[[Request, Context], Request] | None = None
    """
    If provided, this function is called on the incoming request at the beginning of processing by the
    [BrowserMiddleware](@yw-nav-class:BrowserMiddleware), allowing for potential side effects.
    """
    onExit: Callable[[Request, Response, Context], Response] | None = None
    """
    If provided, this function is called on both the incoming request and outgoing response at the end of
    processing by the [BrowserMiddleware](@yw-nav-class:BrowserMiddleware), allowing for potential side effects.
    """


class System(BaseModel):
    """
    Gathers the configuration options related to downloading and storing assets in the local disk.

    The default value is most of the time adapted for most users:

    <code-snippet language="python" highlightedLines="5 9">
    from pathlib import Path

    from youwol.app.environment import (
            Configuration,
            System
        )

    Configuration(
        system=System()
    )
    </code-snippet>
    In a nutshell:

    *  it defines the serving http port to `2000`
    *  it connects to `platform.youwol.com` to download missing assets, using a browser based authentication
    (through cookies)
    *  it persists the assets in a common place on your computer
    (see [LocalEnvironment](@yw-nav-class:models_config.LocalEnvironment))

    The above example is equivalent to:
    <code-snippet language="python">
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
            localEnvironment=LocalEnvironment(),
            browserEnvironment=BrowserEnvironment()
        )
    )
    </code-snippet>
    """

    httpPort: int | None = default_http_port
    """
    Local port on which py-youwol is served.
    It may be overriden using command line argument `--port` when starting youwol.
    """

    tokensStorage: TokensStorageConf | None = TokensStorageSystemKeyring()
    """
    How to store JWT tokens:

    * [TokensStorageSystemKeyring()](@yw-nav-class:TokensStorageSystemKeyring):
    use system keyring
    * [TokensStoragePath()](@yw-nav-class:TokensStoragePath) :
     store in file
    * [TokensStorageInMemory()](@yw-nav-class:TokensStorageInMemory) :
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

    browserEnvironment: BrowserEnvironment = BrowserEnvironment()
    """
    Features related to the interaction with the browser (most importantly regarding caching).
    """


class Command(BaseModel):
    """
    Defines commands that can be triggered using HTTP call. They are served from
    `/admin/custom-commands/$NAME`, where `$NAME` is the name of the command.

    Example:
        <code-snippet language="python" highlightedLines="4 12-19">
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
        </code-snippet>
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
    [FlowSwitcherMiddleware](@yw-nav-class:FlowSwitcherMiddleware).

    Derived implementation must provide the **dispatch** method.

    Example:
        Below is a typical example
        <code-snippet language="python">
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
        </code-snippet>
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
            context: [Context](@yw-nav-class:Context)

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

        <code-snippet language="python">
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
        </code-snippet>

        In a nutshell:

        *  **events**: allows to react to some events, here the `onLoad` event (configuration loaded).
        *  **middlewares**: attribute provide the ability to plug custom middlewares.
        *  **endPoints**: attribute allows to add end-points to the youwol server, usually as
        [Command](@yw-nav-class:Command).

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

    <code-snippet language="python">
    from youwol.app.environment import Configuration

    Configuration()
    </code-snippet>

    Which is equivalent to:
    <code-snippet language="python">
    from youwol.app.environment import Configuration, System, Projects, Customization

    Configuration(
        system=System(),
        projects=Projects(),
        customization=Customization()
    )
    </code-snippet>
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


BrowserCache.update_forward_refs()
