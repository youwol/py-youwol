from dataclasses import dataclass
from fastapi import APIRouter
from typing import List

import youwol.backends.accounts as accounts_backend
import youwol.backends.assets as assets_backend
import youwol.backends.assets_gateway as assets_gtw
import youwol.backends.cdn_apps_server as cdn_apps_server
import youwol.backends.cdn as cdn_backend
import youwol.backends.cdn_sessions_storage as cdn_sessions_storage
import youwol.backends.files as files_backend
import youwol.backends.flux as flux_backend
import youwol.backends.mock as mock_backend
import youwol.backends.stories as stories_backend
import youwol.backends.tree_db as tree_db_backend
from youwol.app.routers.native_backends_config import assets_gtw_config_py_youwol, stories_config_py_youwol, \
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
