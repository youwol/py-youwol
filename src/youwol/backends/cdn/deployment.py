# typing
from typing import List

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.cdn import Configuration, Constants, get_router
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.use_auth_middleware import auth_middleware
from youwol.backends.common.use_minio import minio

# Youwol utilities
from youwol.utils import DocDbClient
from youwol.utils.clients.file_system.minio_file_system import MinioFileSystem
from youwol.utils.http_clients.cdn_backend import LIBRARIES_TABLE
from youwol.utils.servers.fast_api import FastApiMiddleware


class CdnDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                file_system=MinioFileSystem(
                    bucket_name=Constants.namespace,
                    client=minio,
                    # this root path is for backward compatibility
                    root_path="youwol-users/",
                ),
                doc_db=DocDbClient(
                    url_base="http://docdb/api",
                    keyspace_name=Constants.namespace,
                    table_body=LIBRARIES_TABLE,
                    replication_factor=2,
                ),
            )
        )

    def prefix(self) -> str:
        return "/api/cdn"

    def version(self) -> str:
        return "0.3.8"

    def name(self) -> str:
        return "cdn"

    def middlewares(self) -> List[FastApiMiddleware]:
        return [auth_middleware]


app = get_fastapi_app(CdnDeployment())
