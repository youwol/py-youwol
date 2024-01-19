# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.clients import assets_gateway_client
from youwol.backends.common.use_auth_middleware import auth_middleware
from youwol.backends.stories import Configuration, Constants, get_router

# Youwol utilities
from youwol.utils import DocDbClient, StorageClient
from youwol.utils.http_clients.stories_backend import (
    DOCUMENTS_TABLE,
    DOCUMENTS_TABLE_BY_ID,
    STORIES_TABLE,
)
from youwol.utils.servers.fast_api import FastApiMiddleware


class StoriesDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                storage=StorageClient(
                    url_base="http://storage/api", bucket_name=Constants.namespace
                ),
                doc_db_stories=DocDbClient(
                    url_base="http://docdb/api",
                    keyspace_name=Constants.namespace,
                    table_body=STORIES_TABLE,
                    replication_factor=2,
                ),
                doc_db_documents=DocDbClient(
                    url_base="http://docdb/api",
                    keyspace_name=Constants.namespace,
                    table_body=DOCUMENTS_TABLE,
                    secondary_indexes=[DOCUMENTS_TABLE_BY_ID],
                    replication_factor=2,
                ),
                assets_gtw_client=assets_gateway_client,
            )
        )

    def prefix(self) -> str:
        return "/api/stories"

    def version(self) -> str:
        return "0.1.7"

    def name(self) -> str:
        return "stories"

    def middlewares(self) -> list[FastApiMiddleware]:
        return [auth_middleware]


app = get_fastapi_app(StoriesDeployment())
