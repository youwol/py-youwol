# standard library
from collections.abc import Awaitable, Callable

# relative
from .configurations import Configuration, Dependencies
from .root_paths import router


def get_router(
    configuration: (
        Configuration | Callable[[], Configuration | Awaitable[Configuration]]
    )
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )

    return router
