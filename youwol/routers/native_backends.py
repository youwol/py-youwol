from dataclasses import dataclass
from fastapi import APIRouter
from typing import List

import youwol_accounts as accounts_backend
import youwol_assets_backend as assets_backend
import youwol_assets_gateway as assets_gtw
import youwol_cdn_apps_server as cdn_apps_server
import youwol_cdn_backend as cdn_backend
import youwol_cdn_sessions_storage as cdn_sessions_storage
import youwol_files_backend as files_backend
import youwol_flux_backend as flux_backend
import youwol_mock_backend as mock_backend
import youwol_stories_backend as stories_backend
import youwol_tree_db_backend as tree_db_backend
from youwol.routers.native_backends_config import assets_gtw_config_py_youwol, stories_config_py_youwol, \
    cdn_config_py_youwol, cdn_apps_server_config_py_youwol, tree_db_config_py_youwol, assets_backend_config_py_youwol, \
    flux_backend_config_py_youwol, cdn_session_storage_config_py_youwol, files_backend_config_py_youwol, \
    accounts_backend_config_py_youwol, mock_backend_config_py_youwol

router = APIRouter()


@dataclass(frozen=True)
class BackendPlugin:
    prefix: str
    tags: List[str]
    router: APIRouter


backends = [
    BackendPlugin(
        prefix="/api/stories-backend",
        tags=["Stories"],
        router=stories_backend.get_router(stories_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/cdn-backend",
        tags=["CDN"],
        router=cdn_backend.get_router(cdn_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/assets-gateway",
        tags=["Assets gateway"],
        router=assets_gtw.get_router(assets_gtw_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/applications",
        tags=["CDN applications server"],
        router=cdn_apps_server.get_router(cdn_apps_server_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/treedb-backend",
        tags=["treedb"],
        router=tree_db_backend.get_router(tree_db_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/assets-backend",
        tags=["assets"],
        router=assets_backend.get_router(assets_backend_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/flux-backend",
        tags=["flux"],
        router=flux_backend.get_router(flux_backend_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/cdn-sessions-storage",
        tags=["cdn-sessions-storage"],
        router=cdn_sessions_storage.get_router(cdn_session_storage_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/files-backend",
        tags=["files"],
        router=files_backend.get_router(files_backend_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/accounts",
        tags=["accounts"],
        router=accounts_backend.get_router(accounts_backend_config_py_youwol)
    ),
    BackendPlugin(
        prefix="/api/fake",
        tags=["fake"],
        router=mock_backend.get_router(mock_backend_config_py_youwol)
    )
]

for backend in backends:
    router.include_router(router=backend.router, prefix=backend.prefix)
