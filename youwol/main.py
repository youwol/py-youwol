from fastapi import FastAPI, APIRouter, Depends
import uvicorn
from starlette.responses import RedirectResponse

from youwol.configuration.youwol_configuration import yw_config
from youwol.main_args import get_main_arguments

from youwol.middlewares.auth_middleware import AuthMiddleware
from youwol.middlewares.natives_bypass_middleware import NativesBypassMiddleware
from youwol.routers import api, ui

import youwol.routers.packages.router as packages
import youwol.routers.frontends.router as frontends
import youwol.routers.backends.router as backends
import youwol.routers.environment.router as environment

from youwol.configurations import configuration, print_invite

app = FastAPI(
    title="Local Dashboard",
    openapi_prefix=configuration.open_api_prefix,
    dependencies=[Depends(yw_config)])

web_socket = None

app.add_middleware(AuthMiddleware)


def get_web_socket():
    return web_socket


router = APIRouter()

api_bypass_base_paths = [
    "/api/cdn-backend",
    "/api/flux-backend",
    "/api/treedb-backend",
    "/api/assets-backend",
    "/api/assets-gateway"
    ]

app.add_middleware(NativesBypassMiddleware, api_bypass_base_paths=api_bypass_base_paths)

app.include_router(api.router, prefix=configuration.base_path+"/api", tags=["api"])
app.include_router(ui.router, prefix=configuration.base_path+"/ui", tags=["ui"])
app.include_router(environment.router, prefix=configuration.base_path+"/admin/environment", tags=["environment"])
app.include_router(packages.router, prefix=configuration.base_path+"/admin/packages", tags=["packages"])
app.include_router(frontends.router, prefix=configuration.base_path+"/admin/frontends", tags=["frontends"])
app.include_router(backends.router, prefix=configuration.base_path+"/admin/backends", tags=["backends"])


@app.get(configuration.base_path + "/healthz")
async def healthz():
    return {"status": "youwol ok"}


@app.get(configuration.base_path + '/')
async def home():
    return RedirectResponse(url=f'/ui/local-dashboard')


def main():
    main_args = get_main_arguments()
    print_invite(main_args)
    uvicorn.run(app, host="localhost", port=configuration.http_port)


if __name__ == "__main__":
    main()
