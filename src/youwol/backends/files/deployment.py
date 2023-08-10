# typing
from typing import List

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.use_auth_middleware import auth_middleware
from youwol.backends.common.use_minio import minio
from youwol.backends.files import Configuration, Constants, get_router

# Youwol utilities
from youwol.utils.clients.file_system.minio_file_system import MinioFileSystem
from youwol.utils.servers.fast_api import FastApiMiddleware


class FilesDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                file_system=MinioFileSystem(
                    bucket_name=Constants.namespace,
                    client=minio,
                )
            )
        )

    def prefix(self) -> str:
        return "/api/files"

    def version(self) -> str:
        return "0.1.4"

    def name(self) -> str:
        return "files"

    def middlewares(self) -> List[FastApiMiddleware]:
        return [auth_middleware]


app = get_fastapi_app(FilesDeployment())
