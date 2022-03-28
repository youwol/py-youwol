from fastapi import APIRouter

from youwol.environment.youwol_environment import yw_config

import youwol.backends.assets.root_paths as assets
import youwol.backends.assets_gateway.root_paths as assets_gateway
import youwol_cdn_backend as cdn
import youwol.backends.cdn_apps_server.root_paths as cdn_apps_server
import youwol.backends.cdn_sessions_storage.root_paths as cdn_sessions_storage
import youwol.backends.flux.root_paths as flux
import youwol.backends.stories.root_paths as stories
import youwol.backends.treedb.root_paths as treedb
from youwol.web_socket import AdminContextLogger
from youwol_utils.http_clients import get_service_configuration_local

router = APIRouter()
cached_headers = None


async def get_cdn_config():
    config_yw = await yw_config()
    return get_service_configuration_local(
        path_storage=config_yw.pathsBook.local_storage,
        path_docdb=config_yw.pathsBook.local_docdb,
        namespace=cdn.Constants.namespace,
        table_body=cdn.Constants.schema_docdb,
        ctx_logger=AdminContextLogger()
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
