# standard library
from collections.abc import Awaitable

# typing
from typing import Callable, Union

# relative
from .configurations import Configuration, Dependencies
from .root_paths import router


def get_router(
    configuration: Union[
        Configuration, Callable[[], Union[Configuration, Awaitable[Configuration]]]
    ]
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )

    return router
