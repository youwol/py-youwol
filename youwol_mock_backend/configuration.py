from typing import Union, Callable, Awaitable


class Configuration:

    def __init__(self):
        # No configuration for the moment
        pass


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()

    if isinstance(conf, Configuration):
        return conf
    else:
        return await conf
