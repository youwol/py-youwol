# standard library
from dataclasses import dataclass

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends import (
    accounts,
    assets,
    assets_gateway,
    cdn,
    cdn_apps_server,
    cdn_sessions_storage,
    files,
    flux,
    stories,
    tree_db,
)

# relative
from .native_backends_config import (
    accounts_backend_config_py_youwol,
    assets_backend_config_py_youwol,
    assets_gtw_config_py_youwol,
    cdn_apps_server_config_py_youwol,
    cdn_config_py_youwol,
    cdn_session_storage_config_py_youwol,
    files_backend_config_py_youwol,
    flux_backend_config_py_youwol,
    stories_config_py_youwol,
    tree_db_config_py_youwol,
)

router = APIRouter()


@dataclass(frozen=True)
class BackendPlugin:
    prefix: str
    tags: list[str]
    router: APIRouter


backends = [
    BackendPlugin(
        prefix="/api/stories-backend",
        tags=["Stories"],
        router=stories.get_router(stories_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/cdn-backend",
        tags=["CDN"],
        router=cdn.get_router(cdn_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/assets-gateway",
        tags=["Assets gateway"],
        router=assets_gateway.get_router(assets_gtw_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/applications",
        tags=["CDN applications server"],
        router=cdn_apps_server.get_router(cdn_apps_server_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/treedb-backend",
        tags=["treedb"],
        router=tree_db.get_router(tree_db_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/assets-backend",
        tags=["assets"],
        router=assets.get_router(assets_backend_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/flux-backend",
        tags=["flux"],
        router=flux.get_router(flux_backend_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/cdn-sessions-storage",
        tags=["cdn-sessions-storage"],
        router=cdn_sessions_storage.get_router(cdn_session_storage_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/files-backend",
        tags=["files"],
        router=files.get_router(files_backend_config_py_youwol),
    ),
    BackendPlugin(
        prefix="/api/accounts",
        tags=["accounts"],
        router=accounts.get_router(accounts_backend_config_py_youwol),
    ),
]

for backend in backends:
    router.include_router(router=backend.router, prefix=backend.prefix)
