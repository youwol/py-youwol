# standard library
from collections.abc import Awaitable, Callable

# third parties
from pydantic import BaseModel


class Configuration(BaseModel):

    some_property: int = 42


class Dependencies:
    get_configuration: Callable[[], Configuration | Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
