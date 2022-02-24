from pathlib import Path
from typing import List, NamedTuple, Union, Dict, Optional

from pydantic import BaseModel

from youwol_utils import AccessPolicyBody, TableBody, ReadPolicyEnum, SharePolicyEnum
from youwol_utils.clients.docdb.models import Column, TableOptions, OrderingClause


class Group(BaseModel):
    id: str
    path: str


class User(BaseModel):
    name: str
    groups: List[Group]


class FormData(NamedTuple):
    objectName: Union[str, Path]
    objectData: bytes
    objectSize: int
    content_type: str
    content_encoding: str


class AssetResponse(BaseModel):
    assetId: str
    kind: str
    relatedId: str
    name: str
    images: List[str]
    thumbnails: List[str]
    tags: List[str]
    description: str
    groupId: str


class NewAssetBody(BaseModel):
    assetId: Optional[str] = None
    relatedId: str
    kind: str
    groupId: Optional[str] = None
    name: str = ''
    description: str = ''
    tags: List[str] = []
    defaultAccessPolicy: AccessPolicyBody = AccessPolicyBody(
        read=ReadPolicyEnum.forbidden,
        share=SharePolicyEnum.forbidden,
        parameters={}
    )


class PostAssetBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    groupId: Optional[str] = None
    defaultAccessPolicy: AccessPolicyBody = None


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
    name='entities',
    version='0.0',
    columns=[
        Column(name="asset_id", type=scylla_db_text),
        Column(name="related_id", type=scylla_db_text),
        Column(name="group_id", type=scylla_db_text),
        Column(name="kind", type=scylla_db_text),
        Column(name="name", type=scylla_db_text),
        Column(name="images", type=scylla_db_list_text),
        Column(name="thumbnails", type=scylla_db_list_text),
        Column(name="tags", type=scylla_db_list_text),
        Column(name="description", type=scylla_db_text)
    ],
    partition_key=["asset_id"],
    clustering_columns=[]
)

ACCESS_HISTORY = TableBody(
    name='access_history',
    version='0.0',
    columns=[
        Column(name="record_id", type="text"),
        Column(name="asset_id", type="text"),
        Column(name="related_id", type="text"),
        Column(name="username", type="text"),
        Column(name="timestamp", type="int"),
    ],
    partition_key=["record_id"],
    clustering_columns=[]
)

ACCESS_POLICY = TableBody(
    name='access_policy',
    version='0.0',
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
        clustering_order=[OrderingClause(name='consumer_group_id', order='ASC')]
    )
)
