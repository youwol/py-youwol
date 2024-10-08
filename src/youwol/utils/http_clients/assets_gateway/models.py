# typing
from typing import Any

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils.http_clients.assets_backend import (
    PermissionsResp,
    ReadPolicyEnum,
    SharePolicyEnum,
)


class Group(BaseModel):
    id: str
    path: str


class User(BaseModel):
    name: str
    groups: list[Group]


class GroupsResponse(BaseModel):
    groups: list[Group]


class Metadata(BaseModel):
    description: str
    images: list[str]
    thumbnails: list[str]
    kind: str
    name: str
    groupId: str
    tags: list[str]


class PermissionsResponse(BaseModel):
    read: bool
    write: bool
    share: bool


class AssetResponse(BaseModel):
    """
    Asset description.
    """

    assetId: str
    """
    Asset's ID.
    """
    description: str
    """
    Asset's description.
    """
    images: list[str]
    """
    Asset's images URL.
    """
    thumbnails: list[str]
    """
    Asset's thumbnails URL.
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
    name: str
    """
    Asset's name.
    """
    rawId: str
    """
    Asset's raw-id (relevant when the asset is associated to an entity in another database for its 'raw' content).
    """
    groupId: str
    """
    Owning group ID.
    """
    tags: list[str]
    """
    Asset's tags.
    """
    permissions: PermissionsResponse | None


class AssetWithPermissionResponse(AssetResponse):
    permissions: PermissionsResponse | None


class NewAssetResponse(AssetResponse):
    """
    Asset description when creating an asset using
    :func:`create_asset <youwol.backends.assets_gateway.routers.assets_backend.create_asset>`
    """

    itemId: str
    """
    Item ID
    """
    rawResponse: dict[str, Any] | None
    """
    Response from the underlying service manager of the 'raw' part of the asset; if any.
    """


class AssetsResponse(BaseModel):
    assets: list[AssetResponse]


class ImportAssetsBody(BaseModel):
    folderId: str
    assetIds: list[str]


class DriveResponse(BaseModel):
    driveId: str
    name: str
    groupId: str


class DefaultDriveResponse(BaseModel):
    driveId: str
    driveName: str
    downloadFolderId: str
    downloadFolderName: str
    homeFolderId: str
    homeFolderName: str
    desktopFolderId: str
    desktopFolderName: str
    systemFolderId: str
    systemFolderName: str
    systemPackagesFolderId: str
    systemPackagesFolderName: str
    groupId: str


class DrivesResponse(BaseModel):
    drives: list[DriveResponse]


class FolderResponse(BaseModel):
    driveId: str
    folderId: str
    parentFolderId: str
    name: str


class DriveBody(BaseModel):
    name: str


class PutDriveBody(BaseModel):
    name: str
    driveId: str | None = None


class FolderBody(BaseModel):
    name: str


class PutFolderBody(BaseModel):
    name: str
    folderId: str | None = None


class TreeMetadata(BaseModel):
    assetId: str
    rawId: str
    borrowed: bool


class ItemResponse(BaseModel):
    treeId: str
    folderId: str
    rawId: str
    assetId: str
    groupId: str
    driveId: str
    name: str
    kind: str
    borrowed: bool


class ItemsResponse(BaseModel):
    items: list[ItemResponse]


class ChildrenResponse(BaseModel):
    items: list[ItemResponse]
    folders: list[FolderResponse]


class DeletedItemResponse(BaseModel):
    itemId: str
    name: str
    folderId: str
    type: str
    metadata: str


class DeletedResponse(BaseModel):
    folders: list[FolderResponse]
    items: list[DeletedItemResponse]


class MoveBody(BaseModel):
    destinationFolderId: str


class BorrowBody(BaseModel):
    destinationFolderId: str
    itemId: str | None = None


class QueryTreeBody(BaseModel):
    groupId: str
    folderId: str
    recursive: bool
    fluxProject: bool
    queryStr: str


class QueryFlatBody(BaseModel):
    maxResults: int
    whereClauses: list[Any]


class UpdateAssetBody(BaseModel):
    name: str | None = None
    tags: list[str] | None = None
    description: str | None = None


class AccessBody(BaseModel):
    accessPolicy: str | None = None
    tags: list[str] | None = None
    description: str | None = None


class AccessInfoBody(BaseModel):
    binsCount: int


class OwningGroup(BaseModel):
    name: str
    groupId: str


class GroupAccess(BaseModel):
    read: ReadPolicyEnum
    share: SharePolicyEnum
    expiration: None | str


class ExposingGroup(BaseModel):
    name: str
    groupId: str
    access: GroupAccess


class OwnerInfo(BaseModel):
    exposingGroups: list[ExposingGroup]
    defaultAccess: GroupAccess


class ConsumerInfo(BaseModel):
    permissions: PermissionsResp


class AccessInfo(BaseModel):
    owningGroup: OwningGroup
    ownerInfo: None | OwnerInfo
    consumerInfo: ConsumerInfo
