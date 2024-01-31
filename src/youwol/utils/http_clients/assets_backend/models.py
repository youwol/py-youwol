# standard library
from collections.abc import Mapping
from enum import Enum
from pathlib import Path

# typing
from typing import Any, NamedTuple, Optional, Union

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import TableBody
from youwol.utils.clients.docdb.models import Column, OrderingClause, TableOptions


class HealthzResponse(BaseModel):
    status: str = "assets-backend ok"


class ReadPolicyEnum(str, Enum):
    """
    The read policy values.
    """

    forbidden = "forbidden"
    """
    The asset can not be read.
    """
    authorized = "authorized"
    """
    The asset can be read.
    """
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
    """
    Body to update an access policy for an asset & group.
    """

    read: ReadPolicyEnum
    """
    Whether the asset can be read by the group.
    """
    share: SharePolicyEnum
    """
    Whether the asset can be shared by the group.
    """
    parameters: Mapping[str, Any] = {}


class AccessPolicyResp(BaseModel):
    """
    Describes access policy for an asset w/ particular group.
    """

    read: ReadPolicyEnum
    """
    Read policy.
    """
    share: SharePolicyEnum
    """
    Share policy.
    """
    parameters: Mapping[str, Any] = {}
    timestamp: Union[int, None]


class PermissionsResp(BaseModel):
    """
    Describes the permission of a user to consume an asset.
    """

    write: bool
    """
    Write permission enabled or not.
    """
    read: bool
    """
    Read permission enabled or not.
    """
    share: bool
    """
    Share permission enabled or not.
    """
    expiration: Union[int, None]


class Group(BaseModel):
    id: str
    path: str


class User(BaseModel):
    name: str
    groups: list[Group]


class OwningGroup(BaseModel):
    """
    Describes the owning group of an asset.
    """

    name: str
    """
    Group's name.
    """
    groupId: str
    """
    Group's ID.
    """


class GroupAccess(BaseModel):
    read: ReadPolicyEnum
    share: SharePolicyEnum
    expiration: Union[None, str]


class ExposingGroup(BaseModel):
    name: str
    groupId: str
    access: GroupAccess


class OwnerInfo(BaseModel):
    """
    Describes information related to permissions regarding an asset for owners of the asset
    (users subscribed to the asset's owning group).
    """

    exposingGroups: list[ExposingGroup]
    """
    Groups exposing the asset.
    """
    defaultAccess: GroupAccess
    """
    Default access.
    """


class ConsumerInfo(BaseModel):
    """
    Describes information related to permissions regarding an asset for users that are not owners of the asset
    (users subscribed to the asset's owning group).
    """

    permissions: PermissionsResp
    """
    Description of the permissions the user has over the asset.
    """


class AccessInfoResp(BaseModel):
    """
    Access information summary on an asset.
    """

    owningGroup: OwningGroup
    """
    The owning group.
    """
    ownerInfo: Union[None, OwnerInfo]
    """
    Owner information, only available for owners of the asset.
    """
    consumerInfo: ConsumerInfo
    """
    Consumer information, available for all.
    """


class FormData(NamedTuple):
    objectName: Union[str, Path]
    objectData: bytes
    objectSize: int
    content_type: str
    content_encoding: str


class AssetResponse(BaseModel):
    """
    Asset description.
    """

    assetId: str
    """
    Asset's ID.
    """
    kind: str
    """
    Asset's kind.

    This property has a similar purpose to the usual 'extension' of files in a PC:
    it serves at linking actions (e.g. opening applications, right click on the explorer), previews, icon, *etc.*.

    These bindings can be provided through the implementation of 'installers', see for instance those implemented by
    youwol <a href="https://github.com/youwol/installers/blob/main/src/lib/basic/index.ts" target='_blank'> here </a>.
    Installers are referenced in the user's environment using the
    <a href="/applications/@youwol/platform/latest" target='_blank'> platform </a> application.
    """
    rawId: str
    """
    Asset's raw-id (relevant when the asset is associated to an entity in another database for its 'raw' content).
    """
    name: str
    """
    Asset's name.
    """
    images: list[str]
    """
    Asset's images URL.
    """
    thumbnails: list[str]
    """
    Asset's thumbnails URL.
    """
    tags: list[str]
    """
    Asset's tags.
    """
    description: str
    """
    Asset's description.
    """
    groupId: str
    """
    Owning group ID.
    """


class NewAssetBody(BaseModel):
    """
    Body to create a new asset.
    """

    assetId: Optional[str] = None
    """
    Asset's ID, if not provided use a generated uuid.
    """
    rawId: str
    """
    If the asset is associated to an entity in another database, it is the ID of this entity.
    """
    kind: str
    """
    Kind of this asset.
    """
    groupId: Optional[str] = None
    """
    Group ID in which the asset belongs.
    """
    name: str = ""
    """
    Name of the asset.
    """
    description: str = ""
    """
    Description of the asset.
    """
    tags: list[str] = []
    """
    Tags of the asset.
    """
    defaultAccessPolicy: AccessPolicyBody = AccessPolicyBody(
        read=ReadPolicyEnum.forbidden, share=SharePolicyEnum.forbidden, parameters={}
    )
    """
    Default access policy.
    """


class PostAssetBody(BaseModel):
    """
    Body to update an asset.
    """

    name: Optional[str] = None
    """
    New name if provided.
    """
    description: Optional[str] = None
    """
    New description if provided.
    """
    tags: Optional[list[str]] = None
    """
    New tags if provided.
    """
    groupId: Optional[str] = None
    """
    New owning group ID if provided.
    """
    defaultAccessPolicy: Optional[AccessPolicyBody] = None
    """
    New default access policy if provided.
    """


class AddFilesResponse(BaseModel):
    """
    Describes files imported and associated to an asset.
    """

    filesCount: int
    """
    Number of files.
    """
    totalBytes: int
    """
    Total size.
    """


WhereClause = dict


class QueryAssetBody(BaseModel):
    selectClauses: list[dict[str, str]] = []
    whereClauses: list[WhereClause] = []
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
"""
Table definition for the assets service regarding the indexation of assets.
"""


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
"""
Table definition for the assets service regarding the indexation of assets policies.
"""
