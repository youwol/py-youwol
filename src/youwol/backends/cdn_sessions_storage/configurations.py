# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Callable, Union

# Youwol utilities
from youwol.utils import Storage


@dataclass(frozen=True)
class Constants:
    namespace: str = "cdn-sessions-storage"
    default_owner: str = "/youwol-users"


@dataclass(frozen=True)
class Configuration:
    storage: Storage


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
