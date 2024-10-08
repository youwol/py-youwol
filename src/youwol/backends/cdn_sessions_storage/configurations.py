# standard library
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# Youwol utilities
from youwol.utils import Storage


@dataclass(frozen=True)
class Constants:
    """
    Configuration's constants for the service.
    """

    namespace: str = "cdn-sessions-storage"
    """
    namespace of the service
    """
    default_owner: str = "/youwol-users"


@dataclass(frozen=True)
class Configuration:
    """
    Configuration of the service.
    """

    storage: Storage
    """
    File system client using a bucket defined by this
    :attr:`namespace <youwol.backends.cdn_sessions_storage.configurations.Constants.namespace>`.
    """


class Dependencies:
    get_configuration: Callable[[], Configuration | Awaitable[Configuration]]


async def get_configuration() -> Configuration:
    """
    Returns:
        The configuration of the service.
    """
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
