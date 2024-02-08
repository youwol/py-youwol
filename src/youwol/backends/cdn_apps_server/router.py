# standard library
from collections.abc import Awaitable, Callable

# Youwol backends
from youwol.backends.cdn_apps_server.configurations import Configuration, Dependencies

# relative
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
