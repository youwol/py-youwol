# standard library
from dataclasses import dataclass

# typing
from typing import Awaitable, Callable, Dict, Generic, Optional, TypeVar

# Youwol utilities
from youwol.utils.clients.file_system.interfaces import FileSystemInterface


@dataclass(frozen=True)
class Constants:
    namespace: str = "data"


FileSystemImplementation = TypeVar(
    "FileSystemImplementation", bound=FileSystemInterface
)


@dataclass(frozen=True)
class Configuration(Generic[FileSystemImplementation]):
    file_system: FileSystemImplementation
    admin_headers: Optional[Dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
