from typing import Union, List

from pydantic import BaseModel

from youwol_utils.clients.cache import CacheClient, LocalCacheClient, RedisCacheClient
from youwol_utils.clients.docdb import DocDbClient, LocalDocDbClient
from youwol_utils.clients.storage import StorageClient, LocalStorageClient

DocDb = Union[DocDbClient, LocalDocDbClient]
Storage = Union[StorageClient, LocalStorageClient]
Cache = Union[CacheClient, LocalCacheClient, RedisCacheClient]


class Group(BaseModel):
    id: str
    path: str


class User(BaseModel):
    name: str
    groups: List[Group]


class GroupsResponse(BaseModel):
    groups: List[Group]


class GetRecordsBody(BaseModel):
    ids: List[str]
    groupId: str


class RecordsTable(BaseModel):
    primaryKey: str
    id: str
    values: List[str]


class RecordsKeyspace(BaseModel):
    id: str
    groupId: str
    tables: List[RecordsTable]


class RecordsDocDb(BaseModel):
    keyspaces: List[RecordsKeyspace]


class RecordsBucket(BaseModel):
    id: str
    groupId: str
    paths: List[str]


class RecordsStorage(BaseModel):
    buckets: List[RecordsBucket]


class RecordsResponse(BaseModel):
    docdb: RecordsDocDb
    storage: RecordsStorage
