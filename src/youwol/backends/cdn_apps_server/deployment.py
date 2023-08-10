# typing
from typing import List

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.cdn_apps_server import Configuration, get_router
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.clients import assets_gateway_client
from youwol.backends.common.use_auth_middleware_with_cookie import (
    get_auth_middleware_with_cookie,
)

# Youwol utilities
from youwol.utils.servers.fast_api import FastApiMiddleware


class CdnAppsServerDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(Configuration(assets_gtw_client=assets_gateway_client))

    def prefix(self) -> str:
        return "/applications"

    def version(self) -> str:
        return "0.1.4"

    def name(self) -> str:
        return "cdn-apps-server"

    def middlewares(self) -> List[FastApiMiddleware]:
        return [
            get_auth_middleware_with_cookie(redirect_to_login_for_path="/applications")
        ]


app = get_fastapi_app(CdnAppsServerDeployment())
