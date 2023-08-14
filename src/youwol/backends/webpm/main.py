# standard library
import os

# third parties
from fastapi import APIRouter, FastAPI
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

# Youwol backends
from youwol.backends.common.backend_deployment import (
    BackendDeployment,
    add_observability_routes,
)

# relative
from .dependencies import ConfigurationFactory, config_origin_from_host, lifespan
from .paths import router

ConfigurationFactory.set(
    version=os.environ.get("VERSION"),
    oidc_issuer=os.environ.get("OIDC_ISSUER"),
    client_id=os.environ.get("CLIENT_ID"),
    client_secret=os.environ.get("CLIENT_SECRET"),
    assets_gateway_base_url=os.environ.get("ASSETS_GATEWAY_BASE_URL"),
    config_id=os.environ.get("CONFIG_ID"),
    origin=config_origin_from_host(os.environ.get("HOST")),
    default_cdn_client_version=os.environ.get("DEFAULT_CDN_CLIENT_VERSION"),
    root_redirection=os.environ.get("ROOT_REDIRECTION"),
)


class WebpmDeployment(BackendDeployment):
    def name(self) -> str:
        return "webpm"

    def version(self) -> str:
        return ConfigurationFactory.get().version

    def router(self) -> APIRouter:
        return router


app = FastAPI(lifespan=lifespan)
add_observability_routes(app=app, backend_deployment=WebpmDeployment())
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["HEAD", "GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type, Content-Length"],
    allow_credentials=False,
    max_age=7200,
)
app.include_router(router)


@app.middleware("http")
async def add_corp_header(request: Request, call_next: RequestResponseEndpoint):
    response = await call_next(request)
    response.headers["cross-origin-resource-policy"] = "cross-origin"
    return response
