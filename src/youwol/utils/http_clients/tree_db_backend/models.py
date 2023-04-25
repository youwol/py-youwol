# typing
from typing import List, NamedTuple, Optional, TypeVar, Union

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import DocDb, TableBody, get_valid_keyspace_name
from youwol.utils.clients.docdb.models import Column, IdentifierSI, SecondaryIndex

namespace = "tree-db"


class HealthzResponse(BaseModel):
    status: str = "treedb-backend ok"


class DocDbs(NamedTuple):
    items_db: DocDb
    folders_db: DocDb
    drives_db: DocDb
    deleted_db: DocDb

    keyspace_name = get_valid_keyspace_name(namespace)

    items_table_name = "items"
    items_primary_key = "item_id"

    folders_table_name = "folders"
    folders_primary_key = "folder_id"

    drives_table_name = "drives"
    drives_primary_key = "drive_id"

    deleted_table_name = "deleted"
    deleted_primary_key = "deleted_id"


class PublishResponse(BaseModel):
    filesCount: int
    compressedSize: int
    fingerprint: str
    driveId: str


class Group(BaseModel):
    id: str
    path: str


class GroupsResponse(BaseModel):
    groups: List[Group]


class ItemResponse(BaseModel):
    itemId: str
    assetId: str
    rawId: str
    folderId: str
    driveId: str
    groupId: str
    name: str
    kind: str
    metadata: str
    borrowed: bool


class FolderResponse(BaseModel):
    folderId: str
    parentFolderId: str
    driveId: str
    groupId: str
    name: str
    kind: str
    metadata: str


class DriveResponse(BaseModel):
    driveId: str
    groupId: str
    name: str
    metadata: str


class DefaultDriveResponse(BaseModel):
    driveId: str
    driveName: str
    downloadFolderId: str
    downloadFolderName: str
    homeFolderId: str
    homeFolderName: str
    tmpFolderId: str
    tmpFolderName: str
    systemFolderId: str
    systemFolderName: str
    systemPackagesFolderId: str
    systemPackagesFolderName: str
    groupId: str


class EntityResponse(BaseModel):
    entityType: str
    entity: Union[ItemResponse, FolderResponse, DriveResponse]


GroupId = str


class DrivesResponse(BaseModel):
    drives: List[DriveResponse]


class ChildrenResponse(BaseModel):
    items: List[ItemResponse]
    folders: List[FolderResponse]


class ItemsResponse(BaseModel):
    items: List[ItemResponse]


class PathResponse(BaseModel):
    item: Optional[ItemResponse] = None
    folders: List[FolderResponse]
    drive: DriveResponse


WhereClause = dict


class QueryFilesBody(BaseModel):
    whereClauses: List[WhereClause] = []
    maxResults: int = 10


class PurgeResponse(BaseModel):
    foldersCount: int
    itemsCount: int
    items: List[ItemResponse]


class MoveResponse(BaseModel):
    foldersCount: int
    items: List[ItemResponse]


class ItemBody(BaseModel):
    name: str
    kind: str
    itemId: Optional[str] = None
    borrowed: bool = False
    assetId: str = ""
    metadata: str = "{}"


class MoveItemBody(BaseModel):
    targetId: str
    destinationFolderId: str


class RenameBody(BaseModel):
    name: str


class BorrowBody(BaseModel):
    targetId: Optional[str] = None
    destinationFolderId: str


class FolderBody(BaseModel):
    name: str
    kind: str = ""
    metadata: str = ""
    folderId: Optional[str] = None


class DriveBody(BaseModel):
    name: str
    driveId: Optional[str] = None
    metadata: str = ""


class User(BaseModel):
    name: str
    groups: List[str]


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

FILES_TABLE_PARENT_INDEX = SecondaryIndex(
    name="items_by_parent", identifier=IdentifierSI(column_name="folder_id")
)

FILES_TABLE_RELATED_INDEX = SecondaryIndex(
    name="items_by_related", identifier=IdentifierSI(column_name="related_id")
)

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

FOLDERS_TABLE_PARENT_INDEX = SecondaryIndex(
    name="folders_by_parent", identifier=IdentifierSI(column_name="parent_folder_id")
)

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

DRIVES_TABLE_PARENT_INDEX = SecondaryIndex(
    name="drives_by_parent", identifier=IdentifierSI(column_name="group_id")
)

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

DELETED_TABLE_DRIVE_INDEX = SecondaryIndex(
    name="deleted_by_drive", identifier=IdentifierSI(column_name="drive_id")
)

TDocDb = TypeVar("TDocDb")


def create_doc_dbs(factory_db: TDocDb, **kwargs) -> DocDbs:
    files_db = factory_db(
        keyspace_name=DocDbs.keyspace_name,
        table_body=FILES_TABLE,
        secondary_indexes=[FILES_TABLE_PARENT_INDEX, FILES_TABLE_RELATED_INDEX],
        **kwargs,
    )

    folders_db = factory_db(
        keyspace_name=DocDbs.keyspace_name,
        table_body=FOLDERS_TABLE,
        secondary_indexes=[FOLDERS_TABLE_PARENT_INDEX],
        **kwargs,
    )

    drives_db = factory_db(
        keyspace_name=DocDbs.keyspace_name,
        table_body=DRIVES_TABLE,
        secondary_indexes=[DRIVES_TABLE_PARENT_INDEX],
        **kwargs,
    )

    deleted_db = factory_db(
        keyspace_name=DocDbs.keyspace_name,
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
