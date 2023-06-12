# typing
from typing import Awaitable, Callable, Union

# Youwol backends
from youwol.backends.cdn_sessions_storage import Configuration, Dependencies
from youwol.backends.cdn_sessions_storage.root_paths import router


def get_router(
    configuration: Union[
        Configuration, Callable[[], Union[Configuration, Awaitable[Configuration]]]
    ]
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )

    return router
