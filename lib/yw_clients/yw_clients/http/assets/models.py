# standard library
from collections.abc import Mapping
from enum import Enum

# typing
from typing import Any, NamedTuple

# third parties
from pydantic import BaseModel


class ReadPolicyEnum(str, Enum):
    """
    The read policy values.
    """

    FORBIDDEN = "forbidden"
    """
    The asset can not be read.
    """
    AUTHORIZED = "authorized"
    """
    The asset can be read.
    """
    OWNING = "owning"
    EXPIRATION_DATE = "expiration-date"


ReadPolicyEnumFactory = {
    "forbidden": ReadPolicyEnum.FORBIDDEN,
    "authorized": ReadPolicyEnum.AUTHORIZED,
    "owning": ReadPolicyEnum.OWNING,
    "expiration-date": ReadPolicyEnum.EXPIRATION_DATE,
}


class SharePolicyEnum(str, Enum):
    """
    The share policy values.
    """

    FORBIDDEN = "forbidden"
    """
    The asset can not be shared.
    """
    AUTHORIZED = "authorized"
    """
    The asset can be shared.
    """


SharePolicyEnumFactory = {
    "forbidden": SharePolicyEnum.FORBIDDEN,
    "authorized": SharePolicyEnum.AUTHORIZED,
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
    timestamp: int | None


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
    expiration: int | None


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
    """
    Describes access for a group.
    """

    read: ReadPolicyEnum
    """
    Access policy regarding read operations.
    """
    share: SharePolicyEnum
    """
    Access policy regarding share operations.
    """
    expiration: None | str


class ExposingGroup(BaseModel):
    """
    Describes group information regarding access.
    """

    name: str
    """
    Name of the group.
    """
    groupId: str
    """
    ID of the group
    """
    access: GroupAccess
    """
    Access policies associated.
    """


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
    ownerInfo: None | OwnerInfo
    """
    Owner information, only available for owners of the asset.
    """
    consumerInfo: ConsumerInfo
    """
    Consumer information, available for all.
    """


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

    assetId: str | None = None
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
    groupId: str | None = None
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
        read=ReadPolicyEnum.FORBIDDEN, share=SharePolicyEnum.FORBIDDEN, parameters={}
    )
    """
    Default access policy.
    """


class PostAssetBody(BaseModel):
    """
    Body to update an asset.
    """

    name: str | None = None
    """
    New name if provided.
    """
    description: str | None = None
    """
    New description if provided.
    """
    tags: list[str] | None = None
    """
    New tags if provided.
    """
    groupId: str | None = None
    """
    New owning group ID if provided.
    """
    defaultAccessPolicy: AccessPolicyBody | None = None
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


class UpdateAssetBody(BaseModel):
    """
    Describes the body content to update an asset.
    """

    name: str | None = None
    """
    Update the name to this value if provided.
    """
    tags: list[str] | None = None
    """
    Update the tags to this value if provided.
    """
    description: str | None = None
    """
    Update the description to this value if provided.
    """


class QueryAssetBody(BaseModel):
    selectClauses: list[dict[str, str]] = []
    whereClauses: list[WhereClause] = []
    maxResults: int = 10


class ParsedFile(NamedTuple):
    content: bytes
    extension: str
    name: str
