from dataclasses import dataclass
from typing import Union

from fastapi import APIRouter

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment

import youwol.backends.assets.root_paths as assets
import youwol.backends.assets_gateway.root_paths as assets_gateway
import youwol_cdn_backend as cdn
import youwol.backends.cdn_apps_server.root_paths as cdn_apps_server
import youwol.backends.cdn_sessions_storage.root_paths as cdn_sessions_storage
import youwol.backends.flux.root_paths as flux
import youwol.backends.stories.root_paths as stories
import youwol.backends.treedb.root_paths as treedb
from youwol.web_socket import AdminContextLogger

from youwol_utils import TableBody
from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.storage.storage import StorageClient as Storage
from youwol_utils.context import ContextLogger

router = APIRouter()
cached_headers = None


@dataclass(frozen=True)
class ServiceConfiguration:

    storage: Union[Storage, LocalStorage, None]
    doc_db: Union[DocDb, LocalDocDb, None]
    ctx_logger: ContextLogger


def get_service_configuration_local(
        env: YouwolEnvironment,
        namespace: str,
        table_body: TableBody
):

    return ServiceConfiguration(
        storage=LocalStorage(root_path=env.pathsBook.local_storage, bucket_name=namespace),
        doc_db=LocalDocDb(root_path=env.pathsBook.local_docdb,
                          keyspace_name=namespace,
                          table_body=table_body),
        ctx_logger=AdminContextLogger()
    )


async def get_cdn_config():
    env = await yw_config()
    return get_service_configuration_local(
        env=env,
        namespace=cdn.Constants.namespace,
        table_body=cdn.Constants.schema_docdb,
    )
cdn.Dependencies.get_configuration = get_cdn_config
router.include_router(cdn.router, prefix="/api/cdn-backend", tags=["cdn"])

router.include_router(cdn_apps_server.router, prefix="/applications", tags=["cdn applications server"])
router.include_router(treedb.router, prefix="/api/treedb-backend", tags=["treedb"])
router.include_router(assets.router, prefix="/api/assets-backend", tags=["assets"])
router.include_router(flux.router, prefix="/api/flux-backend", tags=["flux"])
router.include_router(stories.router, prefix="/api/stories-backend", tags=["stories"])
router.include_router(assets_gateway.router, prefix="/api/assets-gateway", tags=["assets-gateway"])
router.include_router(cdn_sessions_storage.router, prefix="/api/cdn-sessions-storage", tags=["cdn-sessions-storage"])
