import asyncio
import os
from pathlib import Path

import daemon
import lockfile
import uvicorn
from fastapi import FastAPI, APIRouter, Depends, WebSocket
from starlette.requests import Request
from starlette.responses import RedirectResponse

import youwol.middlewares.custom_dispatch_middleware as custom_dispatch
import youwol.middlewares.dynamic_routing.loading_graph_rules as loading_graph
import youwol.middlewares.dynamic_routing.missing_asset_rules as missing_asset
import youwol.middlewares.dynamic_routing.workspace_explorer_rules as workspace_explorer
from youwol.configuration.configuration_validation import ConfigurationLoadingException
from youwol.environment.auto_download_thread import AssetDownloadThread
from youwol.environment.youwol_environment import YouwolEnvironmentFactory, yw_config, api_configuration, print_invite, \
    YouwolEnvironment
from youwol.main_args import get_main_arguments
from youwol.middlewares.auth_middleware import AuthMiddleware
from youwol.middlewares.browser_caching_middleware import BrowserCachingMiddleware
from youwol.middlewares.dynamic_routing_middleware import DynamicRoutingMiddleware
from youwol.routers import native_backends, admin, authorization
from youwol.routers.environment.download_assets.data import DownloadDataTask
from youwol.routers.environment.download_assets.flux_project import DownloadFluxProjectTask
from youwol.routers.environment.download_assets.package import DownloadPackageTask
from youwol.utils.utils_low_level import start_web_socket, assert_python, shutdown_daemon_script
from youwol.web_socket import WebSocketsStore, AdminContextLogger
from youwol_utils import YouWolException, youwol_exception_handler, YouwolHeaders
from youwol_utils.context import ContextFactory
from youwol_utils.middlewares.root_middleware import RootMiddleware

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

ContextFactory.with_static_data = {
    "env": lambda: yw_config(),
    "download_thread": download_thread
}


app.add_middleware(
    DynamicRoutingMiddleware,
    dynamic_dispatch_rules=[
        workspace_explorer.GetChildrenDispatch(),
        workspace_explorer.GetPermissionsDispatch(),
        workspace_explorer.GetItemDispatch(),
        loading_graph.GetLoadingGraphDispatch(),
        missing_asset.GetRawDispatch(),
        missing_asset.GetMetadataDispatch(),
        missing_asset.PostMetadataDispatch()
    ],
    disabling_header=YouwolHeaders.py_youwol_local_only
)

app.add_middleware(custom_dispatch.CustomDispatchesMiddleware)
app.add_middleware(BrowserCachingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RootMiddleware, ctx_logger=AdminContextLogger())

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


def main():
    assert_python()
    shutdown_script_path = Path().cwd() / "py-youwol.shutdown.sh"
    try:
        download_thread.start()
        conf: YouwolEnvironment = asyncio.run(YouwolEnvironmentFactory.get())
        print_invite(conf=conf, shutdown_script_path=shutdown_script_path if get_main_arguments().daemonize else None)

        if get_main_arguments().daemonize:
            with daemon.DaemonContext(pidfile=lockfile.FileLock("py-youwol")):
                shutdown_script_path.write_text(shutdown_daemon_script(pid=os.getpid()))
                # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
                # noinspection PyTypeChecker
                uvicorn.run(app, host="localhost", port=conf.httpPort)
        else:
            # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
            # noinspection PyTypeChecker
            uvicorn.run(app, host="localhost", port=conf.httpPort)
    except ConfigurationLoadingException as e:
        print(e)
        exit()
    finally:
        download_thread.join()
        shutdown_script_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
