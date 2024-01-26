# standard library
import asyncio

# third parties
from fastapi import Depends, FastAPI, WebSocket
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp

# Youwol application
import youwol.app.middlewares.local_cloud_hybridizers as local_cloud_hybridizer

from youwol.app.environment import (
    CustomMiddleware,
    JwtProviderBearerDynamicIssuer,
    JwtProviderCookieDynamicIssuer,
    JwtProviderPyYouwol,
    YouwolEnvironment,
    api_configuration,
    yw_config,
)
from youwol.app.middlewares import (
    BrowserCachingMiddleware,
    LocalCloudHybridizerMiddleware,
)
from youwol.app.routers import admin, native_backends
from youwol.app.routers.environment import AssetDownloadThread
from youwol.app.routers.environment.download_assets import (
    DownloadDataTask,
    DownloadFluxProjectTask,
    DownloadPackageTask,
    DownloadStoryTask,
)
from youwol.app.routers.environment.download_assets.custom_asset import (
    DownloadCustomAssetTask,
)
from youwol.app.routers.projects import ProjectLoader

# Youwol utilities
from youwol.utils import (
    CleanerThread,
    OidcConfig,
    YouWolException,
    YouwolHeaders,
    factory_local_cache,
    unexpected_exception_handler,
    youwol_exception_handler,
)
from youwol.utils.clients.oidc.tokens_manager import TokensManager
from youwol.utils.context import Context, ContextFactory, InMemoryReporter
from youwol.utils.middlewares import AuthMiddleware, redirect_to_login
from youwol.utils.middlewares.root_middleware import RootMiddleware

# relative
from .web_socket import WsDataStreamer, WsType, start_web_socket

fastapi_app: FastAPI = FastAPI(
    title="Local Dashboard",
    openapi_prefix=api_configuration.open_api_prefix,
    dependencies=[Depends(yw_config)],
)
"""
The fast api application.

The dependency [yw_config](@yw-nav-func:youwol.app.environment.youwol_environment.yw_config) inject the
 [environment](@yw-nav-class:youwol.app.environment.youwol_environment.YouwolEnvironment)
in the target end-points implementation
(see FastAPI's [dependencies injection](https://fastapi.tiangolo.com/tutorial/dependencies/)).
See also [api_configuration](@yw-nav-glob:youwol.app.environment.youwol_environment.api_configuration) regarding
elements related to the global API configuration.

The application is instrumented in the [create_app](@yw-nav-func:youwol.app.fastapi_app.create_app) function.

"""


download_thread = AssetDownloadThread(
    factories={
        "package": DownloadPackageTask,
        "flux-project": DownloadFluxProjectTask,
        "data": DownloadDataTask,
        "story": DownloadStoryTask,
        "custom-asset": DownloadCustomAssetTask,
    },
    worker_count=4,
)

cleaner_thread = CleanerThread()

auth_cache = factory_local_cache(cleaner_thread, "auth_cache")
ContextFactory.with_static_data = {
    "env": yw_config,
    "download_thread": download_thread,
    "cleaner_thread": cleaner_thread,
    "auth_cache": auth_cache,
    "fastapi_app": lambda: fastapi_app,
}


class CustomMiddlewareWrapper(BaseHTTPMiddleware):
    model_config: CustomMiddleware

    def __init__(self, app: ASGIApp, model_config: CustomMiddleware):
        super().__init__(app)
        self.model_config = model_config

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        return await self.model_config.dispatch(
            incoming_request=request,
            call_next=call_next,
            context=Context.from_request(request),
        )


def setup_middlewares(env: YouwolEnvironment):
    """
    Set up the middlewares stack of the [application](@yw-nav-glob:youwol.app.fastapi_app.fastapi_app):
    *  [RootMiddleware](@yw-nav-class:youwol.utils.middlewares.root_middleware.RootMiddleware) using
    [InMemoryReporter](@yw-nav-class:youwol.utils.context.InMemoryReporter) for `logs_reporter` and
    [WsDataStreamer](@yw-nav-class:youwol.app.web_socket.WsDataStreamer) for `data_reporter`.
    *  [AuthMiddleware](@yw-nav-class:youwol.utils.middlewares.authentication.AuthMiddleware)
    using
    [JwtProviderBearerDynamicIssuer](@yw-nav-class:youwol.app.environment.local_auth.JwtProviderBearerDynamicIssuer),
    [JwtProviderCookieDynamicIssuer](@yw-nav-class:youwol.app.environment.local_auth.JwtProviderCookieDynamicIssuer),
    [JwtProviderPyYouwol](@yw-nav-class:youwol.app.environment.local_auth.JwtProviderPyYouwol)
    *  <a href="@yw-nav-class:youwol.app.middlewares.browser_caching_middleware.BrowserCachingMiddleware">
    BrowserCachingMiddleware</a>
    *  the list of [custom middlewares](@yw-nav-class:youwol.app.environment.models.models_config.CustomMiddleware)
    defined in the configuration file.
    *  the <a href="@yw-nav-class:youwol.app.middlewares.hybridizer_middleware.LocalCloudHybridizerMiddleware">
    local/cloud hybrid middleware</a>
     using various [dispatches](@yw-nav-mod:youwol.app.middlewares.local_cloud_hybridizers).

    Parameters:
        env: the current environment, used to inject user defined middlewares.
    """
    fastapi_app.add_middleware(
        LocalCloudHybridizerMiddleware,
        dynamic_dispatch_rules=[
            local_cloud_hybridizer.workspace_explorer_rules.GetChildrenDispatch(),
            local_cloud_hybridizer.workspace_explorer_rules.MoveBorrowInRemoteFolderDispatch(),
            local_cloud_hybridizer.loading_graph_rules.GetLoadingGraph(),
            local_cloud_hybridizer.download_rules.UpdateApplication(),
            local_cloud_hybridizer.download_rules.Download(),
            local_cloud_hybridizer.forward_only_rules.ForwardOnly(),
            local_cloud_hybridizer.deprecated_rules.PostMetadataDeprecated(),
            local_cloud_hybridizer.deprecated_rules.CreateAssetDeprecated(),
        ],
        disabling_header=YouwolHeaders.py_youwol_local_only,
    )

    for middleware in reversed(env.customMiddlewares):
        fastapi_app.add_middleware(CustomMiddlewareWrapper, model_config=middleware)

    fastapi_app.add_middleware(BrowserCachingMiddleware)
    fastapi_app.add_middleware(
        AuthMiddleware,
        predicate_public_path=lambda url: url.path.startswith(
            "/api/accounts/openid_rp/"
        ),
        jwt_providers=[
            JwtProviderBearerDynamicIssuer(),
            JwtProviderCookieDynamicIssuer(
                tokens_manager=TokensManager(
                    storage=env.tokens_storage,
                    oidc_client=OidcConfig(
                        base_url=env.get_remote_info().authProvider.openidBaseUrl,
                    ).for_client(env.get_remote_info().authProvider.openidClient),
                ),
            ),
            JwtProviderPyYouwol(),
        ],
        on_missing_token=lambda url, text: (
            redirect_to_login(url)
            if url.path.startswith("/applications")
            else Response(content=f"Authentication failure : {text}", status_code=403)
        ),
    )

    fastapi_app.add_middleware(
        RootMiddleware, logs_reporter=InMemoryReporter(), data_reporter=WsDataStreamer()
    )


def setup_http_routers():
    """
    Set up the routers of the [application](@yw-nav-glob:youwol.app.fastapi_app.fastapi_app):
    *  [native backends router](@yw-nav-mod:youwol.backends): these routers include the core services of youwol,
    they define services that are available in local and remote environments.
    Beside [cdn_app_server](@ywn-nav-mod:youwol.backends.cdn_app_server) that is served
    under `/applications`, the other services are served under `/api/$SERVICE_NAME` (where `$SERVICE_NAME` is the name
    of the corresponding service).
    *  [local youwol router](@yw-nav-mod:youwol.app.routers): these routers correspond to the services specific to
    the local youwol server, they are served under `/admin`.
    **These services are not available in the online environment.**
    *  the routes `/healthz` and `/`

    Notes:
        While in the local server all services are exposed, in the online environment access to the services
        [tree_db](@yw-nav-mod:youwol.backends.tree_db),
        [files](@yw-nav-mod:youwol.backends.files), [assets](@yw-nav-mod:youwol.backends.assets) and
        [cdn](@yw-nav-mod:youwol.backends.cdn) are **only exposed through
        the [assets-gateway](@yw-nav-mod:youwol.backends.assets_gateway) service**.

    """
    fastapi_app.include_router(native_backends.router)
    fastapi_app.include_router(
        admin.router, prefix=api_configuration.base_path + "/admin"
    )

    @fastapi_app.get(api_configuration.base_path + "/healthz")
    async def healthz():
        return {"status": "py-youwol ok"}

    @fastapi_app.get(api_configuration.base_path + "/")
    async def home():
        return RedirectResponse(
            status_code=308, url="/applications/@youwol/platform/latest"
        )


def setup_web_sockets():
    """
    Install web-sockets handlers, they convey messages from the server to the client (not the other way around).
    Two channels are available:
     * `/ws-logs`: Channel that is responsible to convey messages related to logs (no 'useful' information).
     * `/ws-data`: Channel that is responsible to convey messages related to expected results
      (like result of computations).

    The easiest way for now to consume the different messages sent from `/ws-data` is to use the methods exposed by the
    package [@youwol/local-youwol-client](https://github.com/youwol/local-youwol-client):
    *  `SystemRouter.webSocket.downloadEvent$`
    *  `ProjectsRouter.webSocket.status$`
    *  `ProjectsRouter.webSocket.projectStatus$`
    *  `ProjectsRouter.webSocket.pipelineStatus$`
    *  `ProjectsRouter.webSocket.pipelineStepStatus$`
    *  `ProjectsRouter.webSocket.artifacts$`
    *  `ProjectsRouter.webSocket.stepEvent$`
    *  `LocalCdnRouter.webSocket.status$`
    *  `LocalCdnRouter.webSocket.package$`
    *  `LocalCdnRouter.webSocket.downloadedPackage$`
    *  `LocalCdnRouter.webSocket.packageEvent$`
    *  `EnvironmentRouter.webSocket.status$`
    *  `CustomCommandsRouter.webSocket.log$`


    See also [start_web_socket](@yw-nav-func:youwol.app.web_socket.start_web_socket).
    """

    @fastapi_app.websocket(api_configuration.base_path + "/ws-logs")
    async def ws_logs(ws: WebSocket):
        await start_web_socket(ws, WsType.Log)

    @fastapi_app.websocket(api_configuration.base_path + "/ws-data")
    async def ws_data(ws: WebSocket):
        await start_web_socket(ws, WsType.Data)


def setup_exceptions_handlers():
    """
    Add exceptions handlers, for both ['expected'](@yw-nav-func:youwol.utils.exceptions.youwol_exception_handler)
    and ['unexpected'](@yw-nav-func:youwol.utils.exceptions.unexpected_exception_handler) ones.
    """

    @fastapi_app.exception_handler(YouWolException)
    async def expected_exception(request: Request, exc: YouWolException):
        return await youwol_exception_handler(request, exc)

    @fastapi_app.exception_handler(Exception)
    async def unexpected_exception(request: Request, exc: Exception):
        return await unexpected_exception_handler(request, exc)


async def create_app():
    """
    Create the application:

    *  [setup_middlewares](@yw-nav-func:youwol.app.fastapi_app.setup_middlewares)
    *  [setup_http_routers](@yw-nav-func:youwol.app.fastapi_app.setup_http_routers)
    *  [setup_web_sockets](@yw-nav-func:youwol.app.fastapi_app.setup_web_sockets)
    *  [setup_exceptions_handlers](@yw-nav-func:youwol.app.fastapi_app.setup_exceptions_handlers)
    """
    env = await yw_config()
    setup_middlewares(env=env)
    setup_http_routers()
    setup_web_sockets()
    setup_exceptions_handlers()
    asyncio.ensure_future(ProjectLoader.initialize(env=env))


asyncio.run(create_app())
