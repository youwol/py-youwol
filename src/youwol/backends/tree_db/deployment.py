# typing
from typing import List

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.use_auth_middleware import auth_middleware
from youwol.backends.tree_db import Configuration, get_router

# Youwol utilities
from youwol.utils import DocDbClient
from youwol.utils.http_clients.tree_db_backend import create_doc_dbs
from youwol.utils.servers.fast_api import FastApiMiddleware


class TreeDBDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                doc_dbs=create_doc_dbs(
                    factory_db=DocDbClient,
                    url_base="http://docdb/api",
                    replication_factor=2,
                )
            )
        )

    def prefix(self) -> str:
        return "/api/tree-db"

    def version(self) -> str:
        return "0.3.16"

    def name(self) -> str:
        return "tree-db"

    def middlewares(self) -> List[FastApiMiddleware]:
        return [auth_middleware]


app = get_fastapi_app(TreeDBDeployment())
