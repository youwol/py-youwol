from typing import Union, Callable, Awaitable

from youwol.backends.files import Configuration, Dependencies


def get_router(
    configuration: Union[
        Configuration, Callable[[], Union[Configuration, Awaitable[Configuration]]]
    ]
):
    Dependencies.get_configuration = (
        configuration if callable(configuration) else lambda: configuration
    )
    from youwol.backends.files.root_paths import router

    return router
