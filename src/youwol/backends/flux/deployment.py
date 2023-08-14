# typing
from typing import List

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.clients import assets_gateway_client, cdn_client
from youwol.backends.common.use_auth_middleware import auth_middleware
from youwol.backends.flux import Configuration, Constants, get_router

# Youwol utilities
from youwol.utils import DocDbClient, StorageClient
from youwol.utils.http_clients.flux_backend import COMPONENTS_TABLE, PROJECTS_TABLE
from youwol.utils.servers.fast_api import FastApiMiddleware


class FluxDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                storage=StorageClient(
                    url_base="http://storage/api", bucket_name=Constants.namespace
                ),
                cdn_client=cdn_client,
                doc_db=DocDbClient(
                    url_base="http://docdb/api",
                    keyspace_name=Constants.namespace,
                    table_body=PROJECTS_TABLE,
                    replication_factor=2,
                ),
                doc_db_component=DocDbClient(
                    url_base="http://docdb/api",
                    keyspace_name=Constants.namespace,
                    table_body=COMPONENTS_TABLE,
                    replication_factor=2,
                ),
                assets_gtw_client=assets_gateway_client,
            )
        )

    def prefix(self) -> str:
        return "/api/flux"

    def version(self) -> str:
        return "0.1.19"

    def name(self) -> str:
        return "flux"

    def middlewares(self) -> List[FastApiMiddleware]:
        return [auth_middleware]


app = get_fastapi_app(FluxDeployment())
