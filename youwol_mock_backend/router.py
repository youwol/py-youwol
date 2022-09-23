from typing import Union, Callable, Awaitable

from .configuration import Dependencies, Configuration


def get_router(configuration: Union[
    Configuration,
    Callable[[], Union[
        Configuration,
        Awaitable[Configuration]
    ]
    ]
]):
    Dependencies.get_configuration = configuration if callable(configuration) else lambda: configuration
    from youwol_mock_backend.root_paths import router
    return router
