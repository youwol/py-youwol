from fastapi import FastAPI, APIRouter, Depends, WebSocket
import uvicorn
from starlette.responses import RedirectResponse
from starlette.requests import Request

from asset_auto_download import get_thread_asset_auto_download
from youwol.middlewares.browser_caching_middleware import BrowserCachingMiddleware
from youwol.middlewares.dynamic_routing_middleware import DynamicRoutingMiddleware
from youwol.middlewares.auth_middleware import AuthMiddleware
import youwol.middlewares.dynamic_routing.workspace_explorer_rules as workspace_explorer
import youwol.middlewares.dynamic_routing.live_serving_cdn_rules as live_serving_cdn
import youwol.middlewares.dynamic_routing.live_serving_backends_rules as live_serving_backend
import youwol.middlewares.dynamic_routing.loading_graph_rules as loading_graph
import youwol.middlewares.dynamic_routing.missing_asset_rules as missing_asset

from utils_low_level import start_web_socket
from web_socket import WebSocketsCache
from youwol.configuration.youwol_configuration import yw_config
from youwol.main_args import get_main_arguments


from youwol.routers import native_backends, admin, authorization

from youwol.configurations import configuration, print_invite, assert_python
from youwol_utils import YouWolException, youwol_exception_handler

app = FastAPI(
    title="Local Dashboard",
    openapi_prefix=configuration.open_api_prefix,
    dependencies=[Depends(yw_config)])

web_socket = None


def on_update_available(name: str, version: str):
    print("Update available", name, version)


download_queue, download_event_loop = get_thread_asset_auto_download(on_update_available)
app.add_middleware(
    DynamicRoutingMiddleware,
    dynamic_dispatch_rules=[
        workspace_explorer.GetChildrenDispatch(),
        workspace_explorer.GetPermissionsDispatch(),
        workspace_explorer.GetItemDispatch(),
        loading_graph.GetLoadingGraphDispatch(),
        missing_asset.GetRawDispatch(),
        missing_asset.GetMetadataDispatch(),
        missing_asset.PostMetadataDispatch(),
        live_serving_backend.LiveServingBackendDispatch(),
        live_serving_cdn.LiveServingCdnDispatch()
        ]
    )

app.add_middleware(AuthMiddleware)
app.add_middleware(BrowserCachingMiddleware)

router = APIRouter()

app.include_router(native_backends.router, tags=["native backends"])
app.include_router(admin.router, prefix=configuration.base_path + "/admin", tags=["admin"])
app.include_router(authorization.router, prefix=configuration.base_path + "/authorization", tags=["authorization"])


def get_web_socket():
    return web_socket


@app.exception_handler(YouWolException)
async def exception_handler(request: Request, exc: YouWolException):

    return await youwol_exception_handler(request, exc)


@app.get(configuration.base_path + "/healthz")
async def healthz():
    return {"status": "py-youwol ok"}


@app.get(configuration.base_path + '/')
async def home():
    return RedirectResponse(url=f'/applications/dashboard-developer/latest')


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.regularChannel = ws
    await ws.send_json({})
    await start_web_socket(ws)


def main():
    assert_python()
    main_args = get_main_arguments()
    print_invite(main_args)
    uvicorn.run(app, host="localhost", port=configuration.http_port)


if __name__ == "__main__":
    main()
