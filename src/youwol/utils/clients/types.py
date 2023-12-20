# typing
from typing import Union

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils.clients.cache import CacheClient, LocalCacheClient, RedisCacheClient
from youwol.utils.clients.docdb import DocDbClient, LocalDocDbClient
from youwol.utils.clients.storage import LocalStorageClient, StorageClient

DocDb = Union[DocDbClient, LocalDocDbClient]
Storage = Union[StorageClient, LocalStorageClient]
Cache = Union[CacheClient, LocalCacheClient, RedisCacheClient]


class Group(BaseModel):
    id: str
    path: str


class User(BaseModel):
    name: str
    groups: list[Group]


class GroupsResponse(BaseModel):
    groups: list[Group]


class GetRecordsBody(BaseModel):
    ids: list[str]
    groupId: str


class RecordsTable(BaseModel):
    primaryKey: str
    id: str
    values: list[str]


class RecordsKeyspace(BaseModel):
    id: str
    groupId: str
    tables: list[RecordsTable]


class RecordsDocDb(BaseModel):
    keyspaces: list[RecordsKeyspace]


class RecordsBucket(BaseModel):
    id: str
    groupId: str
    paths: list[str]


class RecordsStorage(BaseModel):
    buckets: list[RecordsBucket]


class RecordsResponse(BaseModel):
    docdb: RecordsDocDb
    storage: RecordsStorage
