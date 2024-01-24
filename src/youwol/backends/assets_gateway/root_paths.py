# third parties
from fastapi import APIRouter, Depends

# Youwol backends
from youwol.backends.assets_gateway.configurations import get_configuration
from youwol.backends.assets_gateway.routers import (
    assets_backend,
    cdn_backend,
    deprecated,
    files_backend,
    flux_backend,
    misc,
    stories_backend,
    treedb_backend,
)

router = APIRouter(tags=["assets-gateway"])
"""
Router of the service, it includes contributions from 4 children router:
*  Under `api/assets-gateway/cdn-backend` are exposed the endpoints of the
[cdn-backend](@yw-nav-mod:youwol.backends.cdn-backend) service.
*  Under `api/assets-gateway/assets-backend` are exposed the endpoints of the
[assets-backend](@yw-nav-mod:youwol.backends.assets-backend) service.
*  Under `api/assets-gateway/files-backend` are exposed the endpoints of the
[files-backend](@yw-nav-mod:youwol.backends.files-backend) service.
*  Under `api/assets-gateway/treedb-backend` are exposed the endpoints of the
[tree_db](@yw-nav-mod:youwol.backends.tree_db) service.
"""


router.include_router(deprecated.router, dependencies=[Depends(get_configuration)])

router.include_router(
    misc.router, prefix="/misc", dependencies=[Depends(get_configuration)]
)

router.include_router(
    cdn_backend.router, prefix="/cdn-backend", dependencies=[Depends(get_configuration)]
)

router.include_router(
    stories_backend.router,
    prefix="/stories-backend",
    dependencies=[Depends(get_configuration)],
)

router.include_router(
    files_backend.router,
    prefix="/files-backend",
    dependencies=[Depends(get_configuration)],
)

router.include_router(
    flux_backend.router,
    prefix="/flux-backend",
    dependencies=[Depends(get_configuration)],
)

router.include_router(
    treedb_backend.router,
    prefix="/treedb-backend",
    dependencies=[Depends(get_configuration)],
)

router.include_router(
    assets_backend.router,
    prefix="/assets-backend",
    dependencies=[Depends(get_configuration)],
)


@router.get("/healthz")
async def healthz():
    return {"status": "assets-gateway ok"}
