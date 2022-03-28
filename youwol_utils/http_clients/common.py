from dataclasses import dataclass
from pathlib import Path
from typing import Union

from youwol_utils import TableBody
from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.storage.storage import StorageClient as Storage
from youwol_utils.context import ContextLogger


@dataclass(frozen=True)
class ServiceConfiguration:

    storage: Union[Storage, LocalStorage, None]
    doc_db: Union[DocDb, LocalDocDb, None]
    ctx_logger: ContextLogger


def get_service_configuration_local(
        path_storage: Path,
        path_docdb: Path,
        namespace: str,
        table_body: TableBody,
        ctx_logger: ContextLogger):

    return ServiceConfiguration(
        storage=LocalStorage(root_path=path_storage, bucket_name=namespace),
        doc_db=LocalDocDb(root_path=path_docdb,
                          keyspace_name=namespace,
                          table_body=table_body),
        ctx_logger=ctx_logger
    )
