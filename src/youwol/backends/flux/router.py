# typing
from typing import Awaitable, Callable, Union

# Youwol backends
from youwol.backends.flux import Configuration, Dependencies, router


def get_router(
    configuration: Union[
        Configuration, Callable[[], Union[Configuration, Awaitable[Configuration]]]
    ]
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )

    return router
