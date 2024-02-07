# standard library
from collections.abc import Awaitable, Callable

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.accounts.configuration import Configuration, Dependencies

# relative
from .root_paths import router


def get_router(
    configuration: (
        Configuration | Callable[[], Configuration | Awaitable[Configuration]]
    )
) -> APIRouter:
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )

    return router
