from enum import Enum
from typing import List, Any

from pydantic import BaseModel


class PackageStatus(Enum):
    NOT_FOUND = 'PackageStatus.NOT_FOUND'
    MISMATCH = 'PackageStatus.MISMATCH'
    SYNC = 'PackageStatus.SYNC'
    PROCESSING = 'PackageStatus.PROCESSING'
    DONE = 'PackageStatus.DONE'


class FluxAppStatus(Enum):
    NOT_FOUND = 'FluxAppStatus.NOT_FOUND'
    MISMATCH = 'FluxAppStatus.MISMATCH'
    SYNC = 'FluxAppStatus.SYNC'
    PROCESSING = 'FluxAppStatus.PROCESSING'
    DONE = 'FluxAppStatus.DONE'


class StoryStatus(Enum):
    NOT_FOUND = 'StoryStatus.NOT_FOUND'
    PROCESSING = 'StoryStatus.PROCESSING'
    DONE = 'StoryStatus.DONE'


class DataAssetStatus(Enum):
    NOT_FOUND = 'DataAssetStatus.NOT_FOUND'
    MISMATCH = 'DataAssetStatus.MISMATCH'
    SYNC = 'DataAssetStatus.SYNC'
    PROCESSING = 'DataAssetStatus.PROCESSING'
    DONE = 'DataAssetStatus.DONE'

class TreeItem(BaseModel):
    name: str
    itemId: str
    group: str
    borrowed: bool
    rawId: str


class Release(BaseModel):
    version: str
    fingerprint: str


class Library(BaseModel):
    assetId: str
    libraryName: str
    namespace: str
    treeItems: List[TreeItem]
    releases: List[Release]
    rawId: str


class Folder(BaseModel):
    folderId: str
    parentFolderId: str
    name: str


class Drive(BaseModel):
    driveId: str
    name: str
    groupId: str


class PathResp(BaseModel):
    group: str
    drive: Drive
    folders: List[Folder]


class LibrariesList(BaseModel):
    libraries: List[Library]


class SyncTarget(BaseModel):
    assetId: str
    version: str


class SyncMultipleBody(BaseModel):
    assetIds: List[SyncTarget]
