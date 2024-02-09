# standard library
from collections.abc import Awaitable, Callable


class Configuration:
    def __init__(self):
        # No configuration for the moment
        pass


class Dependencies:
    get_configuration: Callable[[], Configuration | Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()

    if isinstance(conf, Configuration):
        return conf
    return await conf
