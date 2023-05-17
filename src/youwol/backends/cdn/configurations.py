# standard library
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Awaitable, Callable, Optional, TypeVar, Union

# Youwol utilities
from youwol.utils.clients.docdb.docdb import DocDbClient as RemoteDocDb
from youwol.utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol.utils.clients.file_system import FileSystemInterface
from youwol.utils.clients.storage.local_storage import (
    LocalStorageClient as LocalStorage,
)
from youwol.utils.clients.storage.storage import StorageClient as RemoteStorage
from youwol.utils.http_clients.cdn_backend import LIBRARIES_TABLE

Storage = Union[RemoteStorage, LocalStorage]
DocDb = Union[RemoteDocDb, LocalDocDb]


@dataclass(frozen=True)
class Constants:
    namespace: str = "cdn"
    owner: str = "/youwol-users"
    allowed_prerelease = ["wip", "alpha", "alpha-wip", "beta", "beta-wip"]
    schema_docdb = LIBRARIES_TABLE


FileSystemImplementation = TypeVar(
    "FileSystemImplementation", bound=FileSystemInterface
)


@dataclass(frozen=True)
class Configuration:
    file_system: FileSystemImplementation
    doc_db: DocDb
    required_libs: Optional[Path] = None


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
