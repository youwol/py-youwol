# typing
from typing import Any, Dict, List, Optional, Union

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
    groups: List[Group]


class GroupsResponse(BaseModel):
    groups: List[Group]


class Metadata(BaseModel):
    description: str
    images: List[str]
    thumbnails: List[str]
    kind: str
    name: str
    groupId: str
    tags: List[str]


class PermissionsResponse(BaseModel):
    read: bool
    write: bool
    share: bool
    expiration: Union[int, None]


class AssetResponse(BaseModel):
    assetId: str
    description: str
    images: List[str]
    thumbnails: List[str]
    kind: str
    name: str
    rawId: str
    groupId: str
    tags: List[str]
    permissions: Optional[PermissionsResponse]


class AssetWithPermissionResponse(AssetResponse):
    permissions: Optional[PermissionsResponse]


class NewAssetResponse(AssetResponse):
    itemId: str
    rawResponse: Optional[Dict[str, Any]]


class AssetsResponse(BaseModel):
    assets: List[AssetResponse]


class ImportAssetsBody(BaseModel):
    folderId: str
    assetIds: List[str]


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
    drives: List[DriveResponse]


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
    items: List[ItemResponse]


class ChildrenResponse(BaseModel):
    items: List[ItemResponse]
    folders: List[FolderResponse]


class DeletedItemResponse(BaseModel):
    itemId: str
    name: str
    folderId: str
    type: str
    metadata: str


class DeletedResponse(BaseModel):
    folders: List[FolderResponse]
    items: List[DeletedItemResponse]


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
    whereClauses: List[Any]


class UpdateAssetBody(BaseModel):
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class AccessBody(BaseModel):
    accessPolicy: Optional[str] = None
    tags: Optional[List[str]] = None
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
    exposingGroups: List[ExposingGroup]
    defaultAccess: GroupAccess


class ConsumerInfo(BaseModel):
    permissions: PermissionsResp


class AccessInfo(BaseModel):
    owningGroup: OwningGroup
    ownerInfo: Union[None, OwnerInfo]
    consumerInfo: ConsumerInfo
