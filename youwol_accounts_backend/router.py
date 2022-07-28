from typing import Union, Callable, Awaitable

from youwol_accounts_backend.configuration import Dependencies, Configuration


def get_router(configuration: Union[
    Configuration,
    Callable[[], Union[
        Configuration,
        Awaitable[Configuration]
    ]
    ]
]):
    Dependencies.get_configuration = configuration if callable(configuration) else lambda: configuration
    from youwol_accounts_backend.root_paths import router
    return router
