from fastapi import APIRouter

import youwol.services.backs.cdn.root_paths as cdn
import youwol.services.backs.treedb.root_paths as treedb
import youwol.services.backs.assets.root_paths as assets
import youwol.services.backs.flux.root_paths as flux
import youwol.services.backs.stories.root_paths as stories
import youwol.services.backs.assets_gateway.root_paths as assets_gateway

import youwol.services.backs.cdn_apps_server.root_paths as cdn_apps_server

router = APIRouter()
cached_headers = None


router.include_router(cdn_apps_server.router, prefix="/applications", tags=["cdn applications server"])
router.include_router(cdn.router, prefix="/api/cdn-backend", tags=["cdn"])
router.include_router(treedb.router, prefix="/api/treedb-backend", tags=["treedb"])
router.include_router(assets.router, prefix="/api/assets-backend", tags=["assets"])
router.include_router(flux.router, prefix="/api/flux-backend", tags=["flux"])
router.include_router(stories.router, prefix="/api/stories-backend", tags=["stories"])
router.include_router(assets_gateway.router, prefix="/api/assets-gateway", tags=["assets-gateway"])
