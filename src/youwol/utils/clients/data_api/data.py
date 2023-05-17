# standard library
from dataclasses import dataclass
from pathlib import Path

# Youwol utilities
from youwol.utils import (
    DocDb,
    DocDbClient,
    LocalStorageClient,
    Storage,
    StorageClient,
    TableBody,
    get_local_nosql_instance,
)
from youwol.utils.clients.docdb.models import Column

FILES_TABLE = TableBody(
    name="entities",
    version="0.0",
    columns=[
        Column(name="file_id", type="text"),
        Column(name="file_name", type="text"),
        Column(name="content_type", type="text"),
        Column(name="content_encoding", type="text"),
    ],
    partition_key=["file_id"],
    clustering_columns=[],
)


def get_remote_storage_client(url_base: str):
    return StorageClient(url_base=url_base, bucket_name="data")


def get_remote_docdb_client(url_base: str, replication_factor: int):
    return DocDbClient(
        url_base=url_base,
        keyspace_name="data",
        table_body=FILES_TABLE,
        replication_factor=replication_factor,
    )


def get_local_storage_client(database_path: Path):
    return LocalStorageClient(root_path=database_path / "storage", bucket_name="data")


def get_local_docdb_client(database_path):
    return get_local_nosql_instance(
        root_path=database_path / "docdb",
        keyspace_name="data",
        table_body=FILES_TABLE,
        secondary_indexes=[],
    )


@dataclass(frozen=True)
class DataClient:
    storage: Storage
    docdb: DocDb
