# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Callable, Union

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
    Namespace of the service.
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


@dataclass(frozen=True)
class Configuration:
    """
    Configuration of the service.
    """

    file_system: FileSystemInterface
    """
    File system client using a bucket defined by this
    [namespace](@yw-nav-attr:youwol.backends.cdn.configurations.Constants.namespace).
    """

    doc_db: DocDb
    """
    NoSql client for this [table](@yw-nav-glob:youwol.utils.http_clients.cdn_backend.models.LIBRARIES_TABLE)
    included in this [namespace](@yw-nav-attr:youwol.backends.cdn.configurations.Constants.namespace).
    """


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
