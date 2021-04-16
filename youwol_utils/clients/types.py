from enum import Enum
from typing import Union, List, Mapping, Any

from pydantic import BaseModel

from youwol_utils.clients.docdb import DocDbClient, LocalDocDbClient
from youwol_utils.clients.docdb.local_docdb_in_memory import LocalDocDbInMemoryClient
from youwol_utils.clients.storage import StorageClient, LocalStorageClient
from youwol_utils.clients.cache import CacheClient, LocalCacheClient

DocDb = Union[DocDbClient, LocalDocDbClient, LocalDocDbInMemoryClient]
Storage = Union[StorageClient, LocalStorageClient]
Cache = Union[CacheClient, LocalCacheClient]


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


class ReadPolicyEnum(str, Enum):
    forbidden = "forbidden"
    authorized = "authorized"
    owning = "owning"
    expiration_date = "expiration-date"


#  factory_read = {item.value: item for item in ReadPolicyEnum}
ReadPolicyEnumFactory = {
    "forbidden": ReadPolicyEnum.forbidden,
    "authorized": ReadPolicyEnum.authorized,
    "owning": ReadPolicyEnum.owning,
    "expiration-date": ReadPolicyEnum.expiration_date
    }


class SharePolicyEnum(str, Enum):
    forbidden = "forbidden"
    authorized = "authorized"


SharePolicyEnumFactory = {
    "forbidden": SharePolicyEnum.forbidden,
    "authorized": SharePolicyEnum.authorized,
    }


class AccessPolicyBody(BaseModel):
    read: ReadPolicyEnum
    share: SharePolicyEnum
    parameters: Mapping[str, Any] = {}


class AccessPolicyResp(BaseModel):
    read: ReadPolicyEnum
    share: SharePolicyEnum
    parameters: Mapping[str, Any] = {}
    timestamp: Union[int, None]


class PermissionsResp(BaseModel):
    write: bool
    read: bool
    share: bool
    expiration: Union[int, None]
