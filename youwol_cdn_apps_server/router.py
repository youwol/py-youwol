from typing import Union, Callable, Awaitable
from youwol_cdn_apps_server.configurations import Configuration, Dependencies


def get_router(configuration: Union[
    Configuration,
    Callable[[], Union[
        Configuration,
        Awaitable[Configuration]
        ]
    ]
]):
    Dependencies.get_configuration = configuration if callable(configuration) else lambda: configuration
    from youwol_cdn_apps_server.root_paths import router
    return router

