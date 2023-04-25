# standard library
from dataclasses import dataclass

# typing
from typing import Awaitable, Callable, Dict, Optional, TypeVar, Union

# Youwol utilities
from youwol.utils import DocDb, FileSystemInterface, Storage


@dataclass(frozen=True)
class Constants:
    namespace: str = "assets"
    public_owner = "/youwol-users"


FileSystemImplementation = TypeVar(
    "FileSystemImplementation", bound=FileSystemInterface
)


@dataclass(frozen=True)
class Configuration:
    file_system: FileSystemImplementation
    storage: Storage
    doc_db_asset: DocDb
    doc_db_access_history: DocDb
    doc_db_access_policy: DocDb
    admin_headers: Optional[Dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
