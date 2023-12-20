# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.cdn_sessions_storage import Configuration, Constants, get_router
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.use_auth_middleware_with_cookie import (
    get_auth_middleware_with_cookie,
)

# Youwol utilities
from youwol.utils import StorageClient
from youwol.utils.servers.fast_api import FastApiMiddleware


class CdnSessionsStorageDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                storage=StorageClient(
                    url_base="http://storage/api",
                    bucket_name=Constants.namespace,
                )
            )
        )

    def prefix(self) -> str:
        return "/api/cdn-sessions-storage"

    def version(self) -> str:
        return "0.1.4"

    def name(self) -> str:
        return "cdn-sessions-storage"

    def middlewares(self) -> list[FastApiMiddleware]:
        return [get_auth_middleware_with_cookie()]


app = get_fastapi_app(CdnSessionsStorageDeployment())
