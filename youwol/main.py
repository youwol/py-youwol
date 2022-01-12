import asyncio
import sys

from colorama import Fore, Style
from cowpy import cow

from fastapi import FastAPI, APIRouter, Depends, WebSocket
import uvicorn
from starlette.responses import RedirectResponse
from starlette.requests import Request

from youwol.environment.youwol_environment import YouwolEnvironmentFactory, yw_config, api_configuration
from youwol_utils import YouWolException, youwol_exception_handler

from youwol.context import Context
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.utils_low_level import start_web_socket, assert_python
from youwol.web_socket import WebSocketsStore
from youwol.routers import native_backends, admin, authorization
from youwol.environment.auto_download_thread import AssetDownloadThread
from youwol.routers.environment.download_assets.data import DownloadDataTask
from youwol.routers.environment.download_assets.flux_project import DownloadFluxProjectTask
from youwol.routers.environment.download_assets.package import DownloadPackageTask
from youwol.configuration.configuration_validation import ConfigurationLoadingException
from youwol.middlewares.browser_caching_middleware import BrowserCachingMiddleware
from youwol.middlewares.dynamic_routing_middleware import DynamicRoutingMiddleware
from youwol.middlewares.auth_middleware import AuthMiddleware
import youwol.middlewares.dynamic_routing.workspace_explorer_rules as workspace_explorer
import youwol.middlewares.dynamic_routing.custom_dispatch_rules as custom_dispatch
import youwol.middlewares.dynamic_routing.loading_graph_rules as loading_graph
import youwol.middlewares.dynamic_routing.missing_asset_rules as missing_asset

app = FastAPI(
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
Context.download_thread = download_thread

app.add_middleware(
    DynamicRoutingMiddleware,
    dynamic_dispatch_rules=[
        custom_dispatch.CustomDispatchesRule(),
        workspace_explorer.GetChildrenDispatch(),
        workspace_explorer.GetPermissionsDispatch(),
        workspace_explorer.GetItemDispatch(),
        loading_graph.GetLoadingGraphDispatch(),
        missing_asset.GetRawDispatch(),
        missing_asset.GetMetadataDispatch(),
        missing_asset.PostMetadataDispatch(),
    ]
)

app.add_middleware(AuthMiddleware)
app.add_middleware(BrowserCachingMiddleware)

router = APIRouter()

app.include_router(native_backends.router, tags=["native backends"])
app.include_router(admin.router, prefix=api_configuration.base_path + "/admin", tags=["admin"])
app.include_router(authorization.router, prefix=api_configuration.base_path + "/authorization", tags=["authorization"])


@app.exception_handler(YouWolException)
async def exception_handler(request: Request, exc: YouWolException):
    return await youwol_exception_handler(request, exc)


@app.get(api_configuration.base_path + "/healthz")
async def healthz():
    return {"status": "py-youwol ok"}


@app.get(api_configuration.base_path + '/')
async def home():
    return RedirectResponse(url=f'/applications/@youwol/platform/latest')


@app.websocket(api_configuration.base_path + "/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    WebSocketsStore.userChannel = ws
    await ws.send_json({})
    await start_web_socket(ws)


def print_invite(conf: YouwolEnvironment):
    print(f"""{Fore.GREEN} Configuration loaded successfully {Style.RESET_ALL}.
""")
    print(conf)
    msg = cow.milk_random_cow(f"""
All good, you can now browse to
http://localhost:{conf.http_port}/applications/@youwol/platform/latest
""")
    print(msg)


def main():
    assert_python()
    try:
        download_thread.start()
        conf = asyncio.run(YouwolEnvironmentFactory.get())
        print_invite(conf=conf)
        # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
        # noinspection PyTypeChecker
        uvicorn.run(app, host="localhost", port=conf.http_port)
    except ConfigurationLoadingException as e:
        print(e)
        exit()
    finally:
        download_thread.join()


if __name__ == "__main__":
    main()
