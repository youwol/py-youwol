from dataclasses import dataclass
from typing import List

from fastapi import APIRouter


import youwol.backends.assets.root_paths as assets
import youwol_cdn_backend as cdn
import youwol_assets_gateway as assets_gtw
import youwol_stories_backend as stories_backend
import youwol.backends.cdn_apps_server.root_paths as cdn_apps_server
import youwol.backends.cdn_sessions_storage.root_paths as cdn_sessions_storage
import youwol.backends.flux.root_paths as flux
import youwol.backends.treedb.root_paths as treedb
from youwol.routers.native_backends_config import get_cdn_config, get_assets_gtw_config, stories_config_py_youwol

router = APIRouter()


@dataclass(frozen=True)
class BackendPlugin:
    prefix: str
    tags: List[str]
    router: APIRouter


backends = [
    BackendPlugin(
        prefix="/api/stories-backend",
        tags=["stories"],
        router=stories_backend.get_router(stories_config_py_youwol)
    )
]

for backend in backends:
    router.include_router(router=backend.router, prefix="/api/stories-backend", tags=["stories"])

cdn.Dependencies.get_configuration = get_cdn_config
router.include_router(cdn.router, prefix="/api/cdn-backend", tags=["cdn"])

assets_gtw.Dependencies.get_configuration = get_assets_gtw_config
router.include_router(assets_gtw.router, prefix="/api/assets-gateway", tags=["assets-gateway"])

router.include_router(cdn_apps_server.router, prefix="/applications", tags=["cdn applications server"])
router.include_router(treedb.router, prefix="/api/treedb-backend", tags=["treedb"])
router.include_router(assets.router, prefix="/api/assets-backend", tags=["assets"])
router.include_router(flux.router, prefix="/api/flux-backend", tags=["flux"])
router.include_router(cdn_sessions_storage.router, prefix="/api/cdn-sessions-storage", tags=["cdn-sessions-storage"])
