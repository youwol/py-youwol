from pathlib import Path
from typing import List, NamedTuple, Union, Dict

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
    assetId: str = None
    relatedId: str
    kind: str
    groupId: str = None
    name: str = ''
    description: str = ''
    tags: List[str] = []
    defaultAccessPolicy: AccessPolicyBody = AccessPolicyBody(
        read=ReadPolicyEnum.forbidden,
        share=SharePolicyEnum.forbidden,
        parameters={}
        )


class PostAssetBody(BaseModel):
    name: str = None
    description: str = None
    tags: List[str] = None
    groupId: str = None
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


ASSETS_TABLE = TableBody(
    name='entities',
    columns=[
        Column(name="asset_id", type="text"),
        Column(name="related_id", type="text"),
        Column(name="group_id", type="text"),
        Column(name="kind", type="text"),
        Column(name="name", type="text"),
        Column(name="images", type="list<text>"),
        Column(name="thumbnails", type="list<text>"),
        Column(name="tags", type="list<text>"),
        Column(name="description", type="text")
        ],
    partition_key=["asset_id"],
    clustering_columns=[]
    )

ACCESS_HISTORY = TableBody(
    name='access_history',
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
