# standard library
from collections.abc import Awaitable, Callable

# third parties
from fastapi import APIRouter

# relative
from .configurations import Configuration, Dependencies
from .routers import (
    router_drives,
    router_entities,
    router_folders,
    router_groups,
    router_items,
)

router = APIRouter(tags=["treedb-backend"])
router.include_router(router_entities)
router.include_router(router_items)
router.include_router(router_folders)
router.include_router(router_drives)
router.include_router(router_groups)


def get_router(
    configuration: (
        Configuration | Callable[[], Configuration | Awaitable[Configuration]]
    )
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )

    return router
