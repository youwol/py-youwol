# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Callable, Generic, Optional, TypeVar, Union

# Youwol utilities
from youwol.utils.clients.file_system.interfaces import FileSystemInterface


@dataclass(frozen=True)
class Constants:
    """
    Configuration of the service.
    """

    namespace: str = "data"
    """
    Namespace of the service.
    """


FileSystemImplementation = TypeVar(
    "FileSystemImplementation", bound=FileSystemInterface
)


@dataclass(frozen=True)
class Configuration(Generic[FileSystemImplementation]):
    """
    Configuration of the service.
    """

    file_system: FileSystemImplementation
    """
    File system client using a bucket defined by this
    [namespace](@yw-nav-attr:youwol.backends.files.configurations.Constants.namespace)
    """
    admin_headers: Optional[dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
