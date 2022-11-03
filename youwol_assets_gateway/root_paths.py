from fastapi import APIRouter, Depends

from youwol_assets_gateway.configurations import get_configuration
from youwol_assets_gateway.routers import stories_backend, cdn_backend, files_backend, flux_backend, treedb_backend, \
    assets_backend, deprecated, misc

router = APIRouter(tags=["assets-gateway"])


router.include_router(
    deprecated.router,
    dependencies=[Depends(get_configuration)]
)

router.include_router(
    misc.router,
    prefix="/misc",
    dependencies=[Depends(get_configuration)]
)

router.include_router(
    cdn_backend.router,
    prefix="/cdn-backend",
    dependencies=[Depends(get_configuration)]
)

router.include_router(
    stories_backend.router,
    prefix="/stories-backend",
    dependencies=[Depends(get_configuration)]
)

router.include_router(
    files_backend.router,
    prefix="/files-backend",
    dependencies=[Depends(get_configuration)]
)

router.include_router(
    flux_backend.router,
    prefix="/flux-backend",
    dependencies=[Depends(get_configuration)]
)

router.include_router(
    treedb_backend.router,
    prefix="/treedb-backend",
    dependencies=[Depends(get_configuration)]
)

router.include_router(
    assets_backend.router,
    prefix="/assets-backend",
    dependencies=[Depends(get_configuration)]
)


@router.get("/healthz")
async def healthz():
    return {"status": "assets-gateway ok"}
