# standard library
from enum import Enum
from pathlib import Path

# typing
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, Union

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import TableBody
from youwol.utils.clients.docdb.models import Column, OrderingClause, TableOptions


class HealthzResponse(BaseModel):
    status: str = "assets-backend ok"


class ReadPolicyEnum(str, Enum):
    forbidden = "forbidden"
    authorized = "authorized"
    owning = "owning"
    expiration_date = "expiration-date"


ReadPolicyEnumFactory = {
    "forbidden": ReadPolicyEnum.forbidden,
    "authorized": ReadPolicyEnum.authorized,
    "owning": ReadPolicyEnum.owning,
    "expiration-date": ReadPolicyEnum.expiration_date,
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


class Group(BaseModel):
    id: str
    path: str


class User(BaseModel):
    name: str
    groups: List[Group]


class OwningGroup(BaseModel):
    name: str
    groupId: str


class GroupAccess(BaseModel):
    read: ReadPolicyEnum
    share: SharePolicyEnum
    expiration: Union[None, str]


class ExposingGroup(BaseModel):
    name: str
    groupId: str
    access: GroupAccess


class OwnerInfo(BaseModel):
    exposingGroups: List[ExposingGroup]
    defaultAccess: GroupAccess


class ConsumerInfo(BaseModel):
    permissions: PermissionsResp


class AccessInfoResp(BaseModel):
    owningGroup: OwningGroup
    ownerInfo: Union[None, OwnerInfo]
    consumerInfo: ConsumerInfo


class FormData(NamedTuple):
    objectName: Union[str, Path]
    objectData: bytes
    objectSize: int
    content_type: str
    content_encoding: str


class AssetResponse(BaseModel):
    assetId: str
    kind: str
    rawId: str
    name: str
    images: List[str]
    thumbnails: List[str]
    tags: List[str]
    description: str
    groupId: str


class NewAssetBody(BaseModel):
    assetId: Optional[str] = None
    rawId: str
    kind: str
    groupId: Optional[str] = None
    name: str = ""
    description: str = ""
    tags: List[str] = []
    defaultAccessPolicy: AccessPolicyBody = AccessPolicyBody(
        read=ReadPolicyEnum.forbidden, share=SharePolicyEnum.forbidden, parameters={}
    )


class PostAssetBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    groupId: Optional[str] = None
    defaultAccessPolicy: Optional[AccessPolicyBody] = None


class AddFilesResponse(BaseModel):
    filesCount: int
    totalBytes: int


WhereClause = dict


class QueryAssetBody(BaseModel):
    selectClauses: List[Dict[str, str]] = []
    whereClauses: List[WhereClause] = []
    maxResults: int = 10


class ParsedFile(NamedTuple):
    content: bytes
    extension: str
    name: str


scylla_db_text = "text"
scylla_db_list_text = "list<text>"

ASSETS_TABLE = TableBody(
    name="entities",
    version="0.0",
    columns=[
        Column(name="asset_id", type=scylla_db_text),
        Column(name="related_id", type=scylla_db_text),
        Column(name="group_id", type=scylla_db_text),
        Column(name="kind", type=scylla_db_text),
        Column(name="name", type=scylla_db_text),
        Column(name="images", type=scylla_db_list_text),
        Column(name="thumbnails", type=scylla_db_list_text),
        Column(name="tags", type=scylla_db_list_text),
        Column(name="description", type=scylla_db_text),
    ],
    partition_key=["asset_id"],
    clustering_columns=[],
)

ACCESS_HISTORY = TableBody(
    name="access_history",
    version="0.0",
    columns=[
        Column(name="record_id", type="text"),
        Column(name="asset_id", type="text"),
        Column(name="related_id", type="text"),
        Column(name="username", type="text"),
        Column(name="timestamp", type="int"),
    ],
    partition_key=["record_id"],
    clustering_columns=[],
)

ACCESS_POLICY = TableBody(
    name="access_policy",
    version="0.0",
    columns=[
        Column(name="asset_id", type="text"),
        Column(name="related_id", type="text"),
        Column(name="consumer_group_id", type="text"),
        Column(name="read", type="text"),
        Column(name="share", type="text"),
        Column(name="parameters", type="text"),
        Column(name="timestamp", type="int"),
    ],
    partition_key=["asset_id"],
    clustering_columns=["consumer_group_id"],
    table_options=TableOptions(
        clustering_order=[OrderingClause(name="consumer_group_id", order="ASC")]
    ),
)
