# standard library
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# typing
from typing import Generic, TypeVar

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
"""
Generic type bound to `FileSystemInterface`.
"""


@dataclass(frozen=True)
class Configuration(Generic[FileSystemImplementation]):
    """
    Configuration of the service.
    """

    file_system: FileSystemImplementation
    """
    File system client using a bucket defined by this
    :attr:`namespace <youwol.backends.files.configurations.Constants.namespace>`
    """
    admin_headers: dict[str, str] | None = None


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
