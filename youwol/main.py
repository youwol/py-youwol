from fastapi import FastAPI, APIRouter, Depends
import uvicorn
from starlette.responses import RedirectResponse, JSONResponse
from starlette.requests import Request

from asset_auto_download import start_thread_asset_auto_download
from middlewares.frontends_middleware import FrontsMiddleware


from middlewares.loading_graph_middleware import LoadingGraphMiddleware
from middlewares.missing_asset_middleware import MissingAssetsMiddleware
from youwol.configuration.youwol_configuration import yw_config
from youwol.main_args import get_main_arguments

from youwol.middlewares.auth_middleware import AuthMiddleware
from youwol.middlewares.backends_middleware import BackendsMiddleware
from youwol.routers import api, ui

import youwol.routers.packages.router as packages
import youwol.routers.frontends.router as frontends
import youwol.routers.backends.router as backends
import youwol.routers.environment.router as environment
import youwol.routers.upload.router_packages as upload_packages
import youwol.routers.upload.router_flux_apps as upload_flux_apps
import youwol.routers.upload.router_stories as upload_stories
import youwol.routers.upload.router_data as upload_data
import youwol.routers.download.router_packages as download_packages
import youwol.routers.download.router_flux_apps as download_flux_apps
import youwol.routers.system.router as system
import youwol.routers.local_cdn.router as local_cdn

from youwol.configurations import configuration, print_invite, assert_python
from youwol_utils import YouWolException, log_error

app = FastAPI(
    title="Local Dashboard",
    openapi_prefix=configuration.open_api_prefix,
    dependencies=[Depends(yw_config)])

web_socket = None

download_queue, new_loop = start_thread_asset_auto_download()

app.add_middleware(FrontsMiddleware,
                   frontends_base_path=['ui/flux-builder', 'ui/flux-runner', 'ui/network', 'ui/stories',
                                        'ui/workspace-explorer', 'ui/exhibition-halls']
                   )
app.add_middleware(LoadingGraphMiddleware)
app.add_middleware(MissingAssetsMiddleware,
                   assets_kind=['flux-project', 'package', 'story', 'data'],
                   download_queue=download_queue,
                   download_event_loop=new_loop
                   )
app.add_middleware(BackendsMiddleware)
app.add_middleware(AuthMiddleware)


def get_web_socket():
    return web_socket


router = APIRouter()


app.include_router(api.router, prefix=configuration.base_path+"/api", tags=["api"])
app.include_router(ui.router, prefix=configuration.base_path+"/ui", tags=["ui"])

app.include_router(system.router, prefix=configuration.base_path+"/admin/system",
                   tags=["system"])
app.include_router(environment.router, prefix=configuration.base_path+"/admin/environment", tags=["environment"])
app.include_router(packages.router, prefix=configuration.base_path+"/admin/packages", tags=["packages"])
app.include_router(frontends.router, prefix=configuration.base_path+"/admin/frontends", tags=["frontends"])
app.include_router(backends.router, prefix=configuration.base_path+"/admin/backends", tags=["backends"])
app.include_router(local_cdn.router, prefix=configuration.base_path+"/admin/local-cdn", tags=["local-cdn"])
app.include_router(upload_packages.router, prefix=configuration.base_path+"/admin/upload/packages",
                   tags=["upload packages"])
app.include_router(upload_flux_apps.router, prefix=configuration.base_path+"/admin/upload/flux-apps",
                   tags=["upload flux apps"])
app.include_router(upload_stories.router, prefix=configuration.base_path+"/admin/upload/stories",
                   tags=["upload stories"])
app.include_router(upload_data.router, prefix=configuration.base_path+"/admin/upload/data",
                   tags=["upload data"])
app.include_router(download_packages.router, prefix=configuration.base_path+"/admin/download/packages",
                   tags=["download packages"])
app.include_router(download_flux_apps.router, prefix=configuration.base_path+"/admin/download/flux-apps",
                   tags=["download flux apps"])


@app.exception_handler(YouWolException)
async def youwol_exception_handler(request: Request, exc: YouWolException):

    log_error(f"{exc.detail}", exc.parameters)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": exc.exceptionType,
            "detail": f"{exc.detail}",
            "parameters": exc.parameters
            }
        )


@app.get(configuration.base_path + "/healthz")
async def healthz():
    return {"status": "youwol ok"}


@app.get(configuration.base_path + '/')
async def home():
    return RedirectResponse(url=f'/ui/local-dashboard')


def main():
    assert_python()
    main_args = get_main_arguments()
    print_invite(main_args)
    uvicorn.run(app, host="localhost", port=configuration.http_port)


if __name__ == "__main__":
    main()
