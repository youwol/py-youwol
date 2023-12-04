# typing
from typing import List

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.assets_gateway import Configuration, get_router
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.clients import cdn_client
from youwol.backends.common.use_auth_middleware_with_cookie import (
    get_auth_middleware_with_cookie,
)

# Youwol utilities
from youwol.utils.clients.assets.assets import AssetsClient
from youwol.utils.clients.files import FilesClient
from youwol.utils.clients.flux.flux import FluxClient
from youwol.utils.clients.stories.stories import StoriesClient
from youwol.utils.clients.treedb.treedb import TreeDbClient
from youwol.utils.servers.fast_api import FastApiMiddleware


class AssetsGatewayDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                assets_client=AssetsClient(url_base="http://assets/api/assets"),
                cdn_client=cdn_client,
                files_client=FilesClient(url_base="http://files/api/files"),
                flux_client=FluxClient("http://flux/api/flux"),
                stories_client=StoriesClient(url_base="http://stories/api/stories"),
                treedb_client=TreeDbClient(url_base="http://tree-db/api/tree-db"),
                https=True,
            )
        )

    def prefix(self) -> str:
        return "/api/assets-gateway"

    def version(self) -> str:
        return "1.1.54"

    def name(self) -> str:
        return "assets-gateway"

    def middlewares(self) -> List[FastApiMiddleware]:
        return [get_auth_middleware_with_cookie()]


app = get_fastapi_app(AssetsGatewayDeployment())
