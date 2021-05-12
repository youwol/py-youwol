from typing import List, Any, Union
from pydantic import BaseModel

from youwol_utils import PermissionsResp, ReadPolicyEnum, SharePolicyEnum


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


class PermissionsResponse(BaseModel):
    read: bool
    write: bool
    share: bool
    expiration: Union[int, None]


class NewAssetResponse(AssetResponse):

    treeId: str


class AssetsResponse(BaseModel):
    assets: List[AssetResponse]


class ImportAssetsBody(BaseModel):
    folderId: str
    assetIds: List[str]


class DriveResponse(BaseModel):
    driveId: str
    name: str


class DrivesResponse(BaseModel):
    drives: List[DriveResponse]


class FolderResponse(BaseModel):
    folderId: str
    parentFolderId: str
    name: str


class DriveBody(BaseModel):
    name: str


class PutDriveBody(BaseModel):
    name: str
    driveId: str = None


class FolderBody(BaseModel):
    name: str


class PutFolderBody(BaseModel):
    name: str
    folderId: str = None


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
    name: str = None
    tags: List[str] = None
    description: str = None


class AccessBody(BaseModel):
    accessPolicy: str = None
    tags: List[str] = None
    description: str = None


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
