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
    YouwolEnvironment,
    api_configuration,
    yw_config,
)
from youwol.app.middlewares import (
    BrowserCachingMiddleware,
    JwtProviderBearerDynamicIssuer,
    JwtProviderCookieDynamicIssuer,
    JwtProviderPyYouwol,
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
    youwol_exception_handler,
)
from youwol.utils.clients.oidc.tokens_manager import TokensManager
from youwol.utils.context import Context, ContextFactory, InMemoryReporter
from youwol.utils.middlewares import AuthMiddleware, redirect_to_login
from youwol.utils.middlewares.root_middleware import RootMiddleware

# relative
from .web_socket import WsDataStreamer, WsType, start_web_socket

fastapi_app = FastAPI(
    title="Local Dashboard",
    openapi_prefix=api_configuration.open_api_prefix,
    dependencies=[Depends(yw_config)],
)

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
        on_missing_token=lambda url, text: redirect_to_login(url)
        if url.path.startswith("/applications")
        else Response(content=f"Authentication failure : {text}", status_code=403),
    )

    fastapi_app.add_middleware(
        RootMiddleware, logs_reporter=InMemoryReporter(), data_reporter=WsDataStreamer()
    )

    fastapi_app.include_router(native_backends.router)
    fastapi_app.include_router(
        admin.router, prefix=api_configuration.base_path + "/admin"
    )


async def create_app():
    env = await yw_config()
    setup_middlewares(env=env)
    asyncio.ensure_future(ProjectLoader.initialize(env=env))

    @fastapi_app.exception_handler(YouWolException)
    async def exception_handler(request: Request, exc: YouWolException):
        return await youwol_exception_handler(request, exc)

    @fastapi_app.get(api_configuration.base_path + "/healthz")
    async def healthz():
        return {"status": "py-youwol ok"}

    @fastapi_app.get(api_configuration.base_path + "/")
    async def home():
        return RedirectResponse(
            status_code=308, url="/applications/@youwol/platform/latest"
        )

    @fastapi_app.websocket(api_configuration.base_path + "/ws-logs")
    async def ws_logs(ws: WebSocket):
        await start_web_socket(ws, WsType.Log)

    @fastapi_app.websocket(api_configuration.base_path + "/ws-data")
    async def ws_data(ws: WebSocket):
        await start_web_socket(ws, WsType.Data)


asyncio.run(create_app())
