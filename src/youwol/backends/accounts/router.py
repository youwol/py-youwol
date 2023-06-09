# typing
from typing import Awaitable, Callable, Union

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.accounts.configuration import Configuration, Dependencies


def get_router(
    configuration: Union[
        Configuration, Callable[[], Union[Configuration, Awaitable[Configuration]]]
    ]
) -> APIRouter:
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )
    # Youwol backends
    from youwol.backends.accounts.root_paths import router

    return router
