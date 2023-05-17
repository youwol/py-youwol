# typing
from typing import Awaitable, Callable, Union

# Youwol backends
from youwol.backends.cdn import Configuration, Dependencies


def get_router(
    configuration: Union[
        Configuration, Callable[[], Union[Configuration, Awaitable[Configuration]]]
    ]
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )
    # Youwol backends
    from youwol.backends.cdn.root_paths import router

    return router
