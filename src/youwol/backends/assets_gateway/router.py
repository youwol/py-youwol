# typing
from typing import Awaitable, Callable, Union

# Youwol backends
from youwol.backends.assets_gateway.configurations import Configuration, Dependencies


def get_router(
    configuration: Union[
        Configuration, Callable[[], Union[Configuration, Awaitable[Configuration]]]
    ]
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )
    # Youwol backends
    from youwol.backends.assets_gateway.root_paths import router

    return router
