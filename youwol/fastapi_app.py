from fastapi import FastAPI, Depends, WebSocket
from starlette.requests import Request
from starlette.responses import RedirectResponse

import youwol.middlewares.custom_dispatch_middleware as custom_dispatch
import youwol.middlewares.dynamic_routing.loading_graph_rules as loading_graph
import youwol.middlewares.dynamic_routing.missing_asset_rules as missing_asset
import youwol.middlewares.dynamic_routing.workspace_explorer_rules as workspace_explorer
from youwol.environment.auto_download_thread import AssetDownloadThread
from youwol.environment.youwol_environment import yw_config, api_configuration
from youwol.middlewares.auth_middleware import AuthMiddleware
from youwol.middlewares.browser_caching_middleware import BrowserCachingMiddleware
from youwol.middlewares.dynamic_routing_middleware import DynamicRoutingMiddleware
from youwol.routers import native_backends, admin, authorization
from youwol.routers.environment.download_assets.data import DownloadDataTask
from youwol.routers.environment.download_assets.flux_project import DownloadFluxProjectTask
from youwol.routers.environment.download_assets.package import DownloadPackageTask
from youwol.utils.utils_low_level import start_web_socket
from youwol.web_socket import WebSocketsStore, InMemoryReporter, WsDataStreamer
from youwol_utils import YouWolException, youwol_exception_handler, YouwolHeaders
from youwol_utils.context import ContextFactory
from youwol_utils.middlewares.root_middleware import RootMiddleware

fastapi_app = FastAPI(
    title="Local Dashboard",
    openapi_prefix=api_configuration.open_api_prefix,
    dependencies=[Depends(yw_config)])

download_thread = AssetDownloadThread(
    factories={
        "package": DownloadPackageTask,
        "flux-project": DownloadFluxProjectTask,
        "data": DownloadDataTask
    },
    worker_count=4
)

ContextFactory.with_static_data = {
    "env": lambda: yw_config(),
    "download_thread": download_thread,
    "fastapi_app": lambda: fastapi_app
}


fastapi_app.add_middleware(
    DynamicRoutingMiddleware,
    dynamic_dispatch_rules=[
        workspace_explorer.GetChildrenDispatch(),
        workspace_explorer.GetPermissionsDispatch(),
        workspace_explorer.GetItemDispatch(),
        workspace_explorer.MoveBorrowInRemoteFolderDispatch(),
        loading_graph.GetLoadingGraphDispatch(),
        missing_asset.GetRawDispatch(),
        missing_asset.GetMetadataDispatch(),
        missing_asset.PostMetadataDispatch(),
        missing_asset.CreateAssetDispatch()
    ],
    disabling_header=YouwolHeaders.py_youwol_local_only
)

fastapi_app.add_middleware(custom_dispatch.CustomDispatchesMiddleware)
fastapi_app.add_middleware(BrowserCachingMiddleware)
fastapi_app.add_middleware(AuthMiddleware)
fastapi_app.add_middleware(
    RootMiddleware,
    logs_reporter=InMemoryReporter(),
    data_reporter=WsDataStreamer()
)

fastapi_app.include_router(native_backends.router)
fastapi_app.include_router(admin.router, prefix=api_configuration.base_path + "/admin")
fastapi_app.include_router(authorization.router, prefix=api_configuration.base_path + "/authorization",
                           tags=["authorization"])


@fastapi_app.exception_handler(YouWolException)
async def exception_handler(request: Request, exc: YouWolException):
    return await youwol_exception_handler(request, exc)


@fastapi_app.get(api_configuration.base_path + "/healthz")
async def healthz():
    return {"status": "py-youwol ok"}


@fastapi_app.get(api_configuration.base_path + '/')
async def home():
    return RedirectResponse(status_code=308, url=f'/applications/@youwol/platform/latest')


@fastapi_app.websocket(api_configuration.base_path + "/ws-logs")
async def ws_logs(ws: WebSocket):
    WebSocketsStore.logs = ws
    await start_web_socket(ws)


@fastapi_app.websocket(api_configuration.base_path + "/ws-data")
async def ws_data(ws: WebSocket):
    WebSocketsStore.data = ws
    await start_web_socket(ws)
