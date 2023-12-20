# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.assets import Configuration, Constants, get_router
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.use_auth_middleware import auth_middleware
from youwol.backends.common.use_minio import minio

# Youwol utilities
from youwol.utils import DocDbClient, StorageClient
from youwol.utils.clients.file_system.minio_file_system import MinioFileSystem
from youwol.utils.http_clients.assets_backend import (
    ACCESS_HISTORY,
    ACCESS_POLICY,
    ASSETS_TABLE,
)
from youwol.utils.servers.fast_api import FastApiMiddleware


class AssetsDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        docdb_url_base = "http://docdb/api"
        return get_router(
            Configuration(
                storage=StorageClient(
                    url_base="http://storage/api", bucket_name=Constants.namespace
                ),
                doc_db_asset=DocDbClient(
                    url_base=docdb_url_base,
                    keyspace_name=Constants.namespace,
                    table_body=ASSETS_TABLE,
                    replication_factor=2,
                ),
                doc_db_access_history=DocDbClient(
                    url_base=docdb_url_base,
                    keyspace_name=Constants.namespace,
                    table_body=ACCESS_HISTORY,
                    replication_factor=2,
                ),
                doc_db_access_policy=DocDbClient(
                    url_base=docdb_url_base,
                    keyspace_name=Constants.namespace,
                    table_body=ACCESS_POLICY,
                    replication_factor=2,
                ),
                file_system=MinioFileSystem(
                    bucket_name=Constants.namespace,
                    client=minio,
                ),
            )
        )

    def prefix(self) -> str:
        return "/api/assets"

    def version(self) -> str:
        return "1.0.0"

    def name(self) -> str:
        return "assets"

    def middlewares(self) -> list[FastApiMiddleware]:
        return [auth_middleware]


app = get_fastapi_app(AssetsDeployment())
