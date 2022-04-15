from dataclasses import dataclass
from typing import Union, Type, Callable, Awaitable, Optional, Dict, TypeVar, Generic

from youwol_utils.clients.file_system.interfaces import FileSystemInterface
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware

AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Constants:
    namespace: str = "data"


FileSystemImplementation = TypeVar('FileSystemImplementation', bound=FileSystemInterface)


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
