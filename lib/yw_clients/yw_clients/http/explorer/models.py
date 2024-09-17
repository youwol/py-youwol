# third parties
from pydantic import BaseModel


class PublishResponse(BaseModel):
    filesCount: int
    compressedSize: int
    fingerprint: str
    driveId: str


class Group(BaseModel):
    """
    Response model for a group.
    """

    id: str
    """
    Group ID.
    """
    path: str
    """
    Associated path.
    """


class GroupsResponse(BaseModel):
    """
    Response model for a query over groups.
    """

    groups: list[Group]
    """
    List of groups.
    """


class ItemResponse(BaseModel):
    """
    Response model for a child item (similar to file) of a folder or drive.
    """

    itemId: str
    """
    ID of the item.
    """
    assetId: str
    """
    Associated asset ID.
    """
    rawId: str
    """
    Associated raw ID.
    """
    folderId: str
    """
    Parent folder ID.
    """
    driveId: str
    """
    Parent drive ID.
    """
    groupId: str
    """
    Parent group ID.
    """
    name: str
    """
    Name.
    """
    kind: str
    """
    Asset kind.
    """
    metadata: str

    borrowed: bool
    """
    Whether it is a borrowed item (similar to symbolic link).
    """


class FolderResponse(BaseModel):
    """
    Response model for a child folder (similar to file) of a folder or drive.
    """

    folderId: str
    """
    Folder ID.
    """
    parentFolderId: str
    """
    Parent folder ID.
    """
    driveId: str
    """
    Parent drive ID.
    """
    groupId: str
    """
    Parent group ID.
    """
    name: str
    """
    Name.
    """
    kind: str
    metadata: str


class DriveResponse(BaseModel):
    """
    Response model for a drive.
    """

    driveId: str
    """
    Drive ID.
    """
    groupId: str
    """
    Parent group ID.
    """
    name: str
    """
    Name.
    """
    metadata: str


class DefaultDriveResponse(BaseModel):
    """
    Each group is assigned a default drive, primarily utilized for data reading and writing tasks.
    This drive is linked to a specific organization and includes a set of predefined folders, as outlined here.
    """

    driveId: str
    """
    Drive ID.
    """
    driveName: str
    """
    Drive name.
    """
    downloadFolderId: str
    """
    Id of the `/home/download` folder.
    """
    downloadFolderName: str
    """
    Name of the `/home/download` folder.
    """
    homeFolderId: str
    """
    ID of the `/home` folder.
    """
    homeFolderName: str
    """
    Name of the `/home` folder.
    """
    tmpFolderId: str
    """
    ID of the `/home/system/tmp` folder.
    """
    tmpFolderName: str
    """
    Name of the `/home/system/tmp` folder.
    """
    systemFolderId: str
    """
    ID of the `/home/system` folder.
    """
    systemFolderName: str
    """
    Name of the `/home/system` folder.
    """
    systemPackagesFolderId: str
    """
    ID of the `/home/system/package` folder.
    """
    systemPackagesFolderName: str
    """
    Name of the `/home/system/package` folder.
    """
    groupId: str
    """
    Parent group ID.
    """


class EntityResponse(BaseModel):
    """
    Generic response model for an entity, either Item, Folder or Drive
    """

    entityType: str
    """
    Type of the entity: `item`, `folder`, or `drive`.
    """
    entity: ItemResponse | FolderResponse | DriveResponse
    """
    Associated entity.
    """


GroupId = str
"""
ID of a group
"""


class DrivesResponse(BaseModel):
    """
    Response model for a query over drives.
    """

    drives: list[DriveResponse]
    """
    List of drives.
    """


class ChildrenResponse(BaseModel):
    """
    Response model when requesting children of a folder or drive.
    """

    items: list[ItemResponse]
    """
    List of items (files).
    """
    folders: list[FolderResponse]
    """
    List of folders.
    """


class ItemsResponse(BaseModel):
    """
    Response model for a query over items.
    """

    items: list[ItemResponse]
    """
    List of items.
    """


class PathResponse(BaseModel):
    """
    Response model that describes the path on an entity.
    """

    item: ItemResponse | None = None
    """
    the item, if applicable.
    """
    folders: list[FolderResponse]
    """
    The list of folder description involved in the path of the entity until the parent drive is reached.
    """
    drive: DriveResponse
    """
    Parent drive.
    """


WhereClause = dict


class QueryFilesBody(BaseModel):
    whereClauses: list[WhereClause] = []
    maxResults: int = 10


class PurgeResponse(BaseModel):
    """
    Response when requesting to purge of a drive.
    """

    foldersCount: int
    """
    Number of folders deleted.
    """
    itemsCount: int
    """
    Number of items deleted.
    """
    items: list[ItemResponse]
    """
    The items deleted.
    """


class MoveResponse(BaseModel):
    """
    Response when requesting to move an item or folder.
    """

    foldersCount: int
    """
    Number of folder 'moved'.
    """
    items: list[ItemResponse]
    """
    The list of items 'moved'.
    """


class ItemBody(BaseModel):
    """
    Body specification to create an Item.
    """

    name: str
    """
    Name of the item.
    """
    kind: str
    """
    Kind of the item
    """
    itemId: str | None = None
    """
    Explicit itemId (if needed).
    """
    borrowed: bool = False
    """
    Whether the item is borrowed (e.g. a symbolic link).
    """
    assetId: str = ""
    """
    ID of the corresponding asset.
    """
    metadata: str = "{}"


class MoveItemBody(BaseModel):
    """
    Body specification to move an entity.
    """

    targetId: str
    """
    The ID of the corresponding entity (folder or item).
    """
    destinationFolderId: str
    """
    The destination folder ID.
    """


class RenameBody(BaseModel):
    """
    Body specification to rename an entity.
    """

    name: str
    """
    New name.
    """


class BorrowBody(BaseModel):
    """
    Body specification to borrow an entity (make a symbolic link).
    """

    targetId: str | None = None
    """
    Target item ID.
    """
    destinationFolderId: str
    """
    Destination folder ID.
    """


class FolderBody(BaseModel):
    """
    Body specification to create a folder.
    """

    name: str
    """
    Name.
    """
    kind: str = ""
    metadata: str = ""
    folderId: str | None = None
    """
    Explicit folder ID if needed.
    """


class DriveBody(BaseModel):
    """
    Body specification to create a drive.
    """

    name: str
    """
    Name.
    """
    driveId: str | None = None
    """
    Explicit drive ID if needed.
    """
    metadata: str = ""


class User(BaseModel):
    """
    Description of a user.
    """

    name: str
    """
    Name of the user.
    """
    groups: list[str]
    """
    Group IDs in which the user belongs.
    """
