# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.use_auth_middleware_with_cookie import (
    get_auth_middleware_with_cookie,
)

# Youwol utilities
from youwol.utils.servers.fast_api import FastApiMiddleware

# relative
from .root_paths import router


class MockDeployment(BackendDeployment):
    def version(self) -> str:
        return "0.1.9.dev"

    def router(self) -> APIRouter:
        return router

    def prefix(self) -> str:
        return "/mock"

    def name(self) -> str:
        return "mock"

    def middlewares(self) -> list[FastApiMiddleware]:
        return [
            get_auth_middleware_with_cookie(public_path="/mock/pub"),
        ]


app = get_fastapi_app(MockDeployment())
