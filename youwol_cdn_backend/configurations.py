from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional, Callable, Awaitable

from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.storage.storage import StorageClient as Storage
from youwol_utils.context import ContextLogger
from youwol_utils.http_clients.cdn_backend import LIBRARIES_TABLE


@dataclass(frozen=True)
class Constants:
    namespace: str = "cdn"
    owner: str = "/youwol-users"
    allowed_prerelease = ['wip', 'alpha', 'alpha-wip', 'beta', 'beta-wip']
    schema_docdb = LIBRARIES_TABLE


@dataclass(frozen=True)
class Configuration:

    storage: Union[Storage, LocalStorage]
    doc_db: Union[DocDb, LocalDocDb]
    ctx_logger: ContextLogger
    required_libs: Optional[Path] = None


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    return await Dependencies.get_configuration()
