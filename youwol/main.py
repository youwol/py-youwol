from fastapi import FastAPI, APIRouter, Depends
import uvicorn
from starlette.responses import RedirectResponse
from starlette.requests import Request

from asset_auto_download import start_thread_asset_auto_download
from middlewares.cross_origin_middleware import CrossOriginMiddleware
from middlewares.live_serving_cdn_middleware import LiveServingCdnMiddleware

from middlewares.loading_graph_middleware import LoadingGraphMiddleware
from middlewares.missing_asset_middleware import MissingAssetsMiddleware
from youwol.configuration.youwol_configuration import yw_config
from youwol.main_args import get_main_arguments

from youwol.middlewares.auth_middleware import AuthMiddleware
from youwol.middlewares.live_serving_backends_middleware import LiveServingBackendsMiddleware

from youwol.routers import native_backends, admin, authorization

from youwol.configurations import configuration, print_invite, assert_python
from youwol_utils import YouWolException, youwol_exception_handler

app = FastAPI(
    title="Local Dashboard",
    openapi_prefix=configuration.open_api_prefix,
    dependencies=[Depends(yw_config)])

web_socket = None

download_queue, new_loop = start_thread_asset_auto_download()

app.add_middleware(CrossOriginMiddleware,
                   frontends_base_path=['ui/flux-builder', 'ui/flux-runner', 'ui/network', 'ui/stories',
                                        'ui/workspace-explorer', 'ui/exhibition-halls']
                   )
app.add_middleware(LiveServingCdnMiddleware)

app.add_middleware(LoadingGraphMiddleware)
app.add_middleware(MissingAssetsMiddleware,
                   assets_kind=['flux-project', 'package', 'story', 'data'],
                   download_queue=download_queue,
                   download_event_loop=new_loop
                   )
app.add_middleware(LiveServingBackendsMiddleware)
app.add_middleware(AuthMiddleware)

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
