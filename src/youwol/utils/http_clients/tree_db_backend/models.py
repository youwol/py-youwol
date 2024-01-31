# standard library
from dataclasses import dataclass

# typing
from typing import Any, Optional, Union

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import DocDb, TableBody
from youwol.utils.clients.docdb.models import Column, IdentifierSI, SecondaryIndex


class HealthzResponse(BaseModel):
    status: str = "treedb-backend ok"


keyspace_name = "tree_db"


@dataclass(frozen=True)
class DocDbs:
    """
    ScyllaDB tables used by the `treedb-backend` service.
    """

    items_db: DocDb
    """
    Table for items, see [FILES_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.FILES_TABLE).
    """
    folders_db: DocDb
    """
    Table for folders, see [FOLDERS_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.FOLDERS_TABLE).
    """
    drives_db: DocDb
    """
    Table for drives, see [DRIVES_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.DRIVES_TABLE).
    """
    deleted_db: DocDb
    """
    Table for deleted entities, see
     [DELETED_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.DELETED_TABLE).
    """


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
    entity: Union[ItemResponse, FolderResponse, DriveResponse]
    """
    Associated entity.
    """


GroupId = str


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

    item: Optional[ItemResponse] = None
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
    itemId: Optional[str] = None
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

    targetId: Optional[str] = None
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
    folderId: Optional[str] = None
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
    driveId: Optional[str] = None
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


class GetRecordsBody(BaseModel):
    folderId: str


FILES_TABLE = TableBody(
    name="items",
    version="0.0",
    columns=[
        Column(name="item_id", type="text"),
        Column(name="folder_id", type="text"),
        Column(name="drive_id", type="text"),
        Column(name="related_id", type="text"),
        Column(name="group_id", type="text"),
        Column(name="name", type="text"),
        Column(name="type", type="text"),
        Column(name="metadata", type="text"),
    ],
    partition_key=["item_id"],
    clustering_columns=[],
)
"""
Table definition for the [tree_db](@yw-nav-mod:youwol.backends.tree_db) service regarding the indexation
 of files (e.g. items).
"""

FILES_TABLE_PARENT_INDEX = SecondaryIndex(
    name="items_by_parent", identifier=IdentifierSI(column_name="folder_id")
)
"""
Secondary index for [FILES_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.FILES_TABLE) to query by
parent's folder ID.
"""


FILES_TABLE_RELATED_INDEX = SecondaryIndex(
    name="items_by_related", identifier=IdentifierSI(column_name="related_id")
)
"""
Secondary index for [FILES_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.FILES_TABLE) to query by
related id (i.e. asset id).
"""

FOLDERS_TABLE = TableBody(
    name="folders",
    version="0.0",
    columns=[
        Column(name="folder_id", type="text"),
        Column(name="parent_folder_id", type="text"),
        Column(name="drive_id", type="text"),
        Column(name="group_id", type="text"),
        Column(name="name", type="text"),
        Column(name="type", type="text"),
        Column(name="metadata", type="text"),
    ],
    partition_key=["folder_id"],
    clustering_columns=[],
)
"""
Table definition for the  [tree_db](@yw-nav-mod:youwol.backends.tree_db) service regarding the indexation of folders.
"""

FOLDERS_TABLE_PARENT_INDEX = SecondaryIndex(
    name="folders_by_parent", identifier=IdentifierSI(column_name="parent_folder_id")
)
"""
Secondary index for [FOLDERS_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.FOLDERS_TABLE)
to query by parent's folder ID.
"""

DRIVES_TABLE = TableBody(
    name="drives",
    version="0.0",
    columns=[
        Column(name="drive_id", type="text"),
        Column(name="group_id", type="text"),
        Column(name="name", type="text"),
        Column(name="metadata", type="text"),
    ],
    partition_key=["drive_id"],
    clustering_columns=[],
)
"""
Table definition for the  [tree_db](@yw-nav-mod:youwol.backends.tree_db) service regarding the indexation of drives.
"""


DRIVES_TABLE_PARENT_INDEX = SecondaryIndex(
    name="drives_by_parent", identifier=IdentifierSI(column_name="group_id")
)
"""
Secondary index for [DRIVES_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.DRIVES_TABLE)
to query by parent's group ID.
"""

DELETED_TABLE = TableBody(
    name="deleted",
    version="0.0",
    columns=[
        Column(name="deleted_id", type="text"),
        Column(name="drive_id", type="text"),
        Column(name="group_id", type="text"),
        Column(name="related_id", type="text"),
        Column(name="name", type="text"),
        Column(name="type", type="text"),
        Column(name="kind", type="text"),
        Column(name="metadata", type="text"),
        Column(name="parent_folder_id", type="text"),
    ],
    partition_key=["deleted_id"],
    clustering_columns=[],
)
"""
Table definition for the  [tree_db](@yw-nav-mod:youwol.backends.tree_db) service regarding the indexation of items
 scheduled for deletion (in the trash, before purge).
"""


DELETED_TABLE_DRIVE_INDEX = SecondaryIndex(
    name="deleted_by_drive", identifier=IdentifierSI(column_name="drive_id")
)
"""
Secondary index for [DELETED_TABLE](@yw-nav-glob:youwol.utils.http_clients.tree_db_backend.models.DELETED_TABLE)
to query by parent's drive ID.
"""


def create_doc_dbs(factory_db: Any, **kwargs) -> DocDbs:
    files_db = factory_db(
        keyspace_name=keyspace_name,
        table_body=FILES_TABLE,
        secondary_indexes=[FILES_TABLE_PARENT_INDEX, FILES_TABLE_RELATED_INDEX],
        **kwargs,
    )

    folders_db = factory_db(
        keyspace_name=keyspace_name,
        table_body=FOLDERS_TABLE,
        secondary_indexes=[FOLDERS_TABLE_PARENT_INDEX],
        **kwargs,
    )

    drives_db = factory_db(
        keyspace_name=keyspace_name,
        table_body=DRIVES_TABLE,
        secondary_indexes=[DRIVES_TABLE_PARENT_INDEX],
        **kwargs,
    )

    deleted_db = factory_db(
        keyspace_name=keyspace_name,
        table_body=DELETED_TABLE,
        secondary_indexes=[DELETED_TABLE_DRIVE_INDEX],
        **kwargs,
    )

    doc_dbs = DocDbs(
        items_db=files_db,
        folders_db=folders_db,
        drives_db=drives_db,
        deleted_db=deleted_db,
    )

    return doc_dbs
