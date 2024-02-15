# standard library
from collections.abc import Awaitable, Callable

# third parties
from fastapi import APIRouter

# relative
from .configurations import Configuration, Dependencies
from .routers import (
    router_access,
    router_assets,
    router_files,
    router_images,
    router_permissions,
    router_raw,
)

router = APIRouter(tags=["assets-backend"])
router.include_router(router_files)
router.include_router(router_images)
router.include_router(router_raw)
router.include_router(router_permissions)
router.include_router(router_access)
router.include_router(router_assets)


def get_router(
    configuration: (
        Configuration | Callable[[], Configuration | Awaitable[Configuration]]
    )
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )
    return router
