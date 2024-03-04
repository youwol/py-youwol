# standard library
from collections.abc import Awaitable, Callable

# relative
from .configurations import Configuration, Dependencies


def get_router(
    configuration: (
        Configuration | Callable[[], Configuration | Awaitable[Configuration]]
    )
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )
    # relative
    from .root_paths import router

    return router
