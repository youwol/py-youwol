# typing
from typing import Any, Optional, Union

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
    assetId: str
    description: str
    images: list[str]
    thumbnails: list[str]
    kind: str
    name: str
    rawId: str
    groupId: str
    tags: list[str]
    permissions: Optional[PermissionsResponse]


class AssetWithPermissionResponse(AssetResponse):
    permissions: Optional[PermissionsResponse]


class NewAssetResponse(AssetResponse):
    """
    Asset description when creating an asset using
    [create_asset](@yw-nav-func:youwol.backends.assets_gateway.routers.assets_backend.create_asset)
    """

    itemId: str
    """
    Item ID
    """
    rawResponse: Optional[dict[str, Any]]
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
    driveId: Optional[str] = None


class FolderBody(BaseModel):
    name: str


class PutFolderBody(BaseModel):
    name: str
    folderId: Optional[str] = None


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
    itemId: Optional[str] = None


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
    name: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = None


class AccessBody(BaseModel):
    accessPolicy: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = None


class AccessInfoBody(BaseModel):
    binsCount: int


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
    exposingGroups: list[ExposingGroup]
    defaultAccess: GroupAccess


class ConsumerInfo(BaseModel):
    permissions: PermissionsResp


class AccessInfo(BaseModel):
    owningGroup: OwningGroup
    ownerInfo: Union[None, OwnerInfo]
    consumerInfo: ConsumerInfo
