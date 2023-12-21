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
"""
See [LocalDocDb](@yw-nav-class:youwol.utils.clients.docdb.local_docdb.LocalDocDbClient) or
[RemoteDocDb](@yw-nav-class:youwol.utils.clients.docdb.docdb.DocDbClient).
"""


@dataclass(frozen=True)
class Constants:
    """
    Configuration's constants for the service.
    """

    namespace: str = "cdn"
    """
    namespace of the service
    """

    owner: str = "/youwol-users"
    allowed_prerelease = ["wip", "alpha", "alpha-wip", "beta", "beta-wip"]
    """
    Prerelease allowed.
    """

    schema_docdb = LIBRARIES_TABLE
    """
    [Schema](@yw-nav-glob:youwol.utils.http_clients.cdn_backend.models.LIBRARIES_TABLE) of the no-sql database.
    """


FileSystemImplementation = TypeVar(
    "FileSystemImplementation", bound=FileSystemInterface
)
"""
Type var specifying implementation that adhere to
[FileSystemInterface](@yw-nav-class:youwol.utils.clients.file_system.interfaces.FileSystemInterface).
"""


@dataclass(frozen=True)
class Configuration:
    """
    Configuration of the service.
    """

    file_system: FileSystemImplementation
    """
    File system storage client.
    """

    doc_db: DocDb
    """
    NoSql client.
    """

    required_libs: Optional[Path] = None


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
