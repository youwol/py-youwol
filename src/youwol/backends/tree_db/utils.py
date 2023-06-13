# standard library
import base64
import json

# typing
from typing import Any, Dict, List, Mapping, Union

# third parties
from fastapi import HTTPException

# Youwol utilities
from youwol.utils import DocDb, asyncio, decode_id, get_all_individual_groups, log_info
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    DriveResponse,
    FolderResponse,
    ItemResponse,
)

# relative
from .configurations import Configuration, Constants


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = config.admin_headers if config.admin_headers else {}
    log_info("Successfully retrieved authorization for resources creation")
    doc_dbs = config.doc_dbs
    log_info("Ensure items_db table")
    await doc_dbs.items_db.ensure_table(headers=headers)
    log_info("Ensure folders_db table")
    await doc_dbs.folders_db.ensure_table(headers=headers)
    log_info("Ensure drives_db table")
    await doc_dbs.drives_db.ensure_table(headers=headers)
    log_info("Ensure deleted_db table")
    await doc_dbs.deleted_db.ensure_table(headers=headers)

    log_info("resources initialization done")


def to_group_id(group_path: Union[str, None]) -> str:
    if group_path == "private" or group_path is None:
        return "private"
    b = str.encode(group_path)
    return base64.urlsafe_b64encode(b).decode()


def to_owner(group_id: str) -> Union[str, None]:
    if group_id == "private":
        return None
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()


async def get_group(
    primary_key: str,
    primary_value: Union[str, float, int, bool],
    groups: List[str],
    doc_db: DocDb,
    headers: Mapping[str, str],
):
    requests = [
        doc_db.query(
            query_body=f"{primary_key}=${primary_value}#1", owner=group, headers=headers
        )
        for group in groups
    ]

    responses = await asyncio.gather(*requests)
    group = next((g for i, g in enumerate(groups) if responses[i]["documents"]), -1)
    return group


def doc_to_item(doc, with_attrs=None):
    with_attrs = with_attrs or {}

    def value(key: str):
        return doc[key] if key not in with_attrs else with_attrs[key]

    metadata = json.loads(value("metadata"))
    return ItemResponse(
        itemId=value("item_id"),
        assetId=value("related_id"),
        rawId=decode_id(value("related_id")),
        folderId=value("folder_id"),
        driveId=value("drive_id"),
        groupId=value("group_id"),
        name=value("name"),
        kind=value("type"),
        metadata=value("metadata"),
        borrowed=metadata["borrowed"] if "borrowed" in metadata else False,
    )


def item_to_doc(item: ItemResponse):
    return {
        "item_id": item.itemId,
        "related_id": item.assetId,
        "folder_id": item.folderId,
        "drive_id": item.driveId,
        "group_id": item.groupId,
        "name": item.name,
        "type": item.kind,
        "metadata": item.metadata,
    }


def doc_to_folder(doc, with_attrs=None):
    with_attrs = with_attrs or {}

    def value(key: str):
        return doc[key] if key not in with_attrs else with_attrs[key]

    return FolderResponse(
        folderId=value("folder_id"),
        parentFolderId=value("parent_folder_id"),
        driveId=value("drive_id"),
        groupId=value("group_id"),
        name=value("name"),
        kind=value("type"),
        metadata=value("metadata"),
    )


def folder_to_doc(folder: FolderResponse):
    return {
        "folder_id": folder.folderId,
        "parent_folder_id": folder.parentFolderId,
        "drive_id": folder.driveId,
        "group_id": folder.groupId,
        "name": folder.name,
        "type": folder.kind,
        "metadata": folder.metadata,
    }


def doc_to_drive_response(doc):
    return DriveResponse(
        driveId=doc["drive_id"],
        groupId=doc["group_id"],
        name=doc["name"],
        metadata=doc["metadata"],
    )


async def ensure_drive(
    drive_id: str, group_id: str, docdb_drive: DocDb, headers: Dict[str, Any]
):
    try:
        await docdb_drive.get_document(
            partition_keys={"drive_id": drive_id},
            clustering_keys={},
            owner=group_id,
            headers=headers,
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Drive not found")
        raise e


async def ensure_folder(
    folder_id: str, group_id: str, docdb_folder: DocDb, headers: Dict[str, Any]
):
    try:
        await docdb_folder.get_document(
            partition_keys={"folder_id": folder_id},
            clustering_keys={},
            owner=group_id,
            headers=headers,
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Folder not found")
        raise e


def delete_folder(
    folder_id: str, group_id: str, docdb_folders: DocDb, headers: Dict[str, Any]
):
    return docdb_folders.delete_document(
        doc={"folder_id": folder_id}, owner=group_id, headers=headers
    )


def delete_item(
    item_id: str, group_id: str, docdb_items: DocDb, headers: Dict[str, Any]
):
    return docdb_items.delete_document(
        doc={"item_id": item_id}, owner=group_id, headers=headers
    )


async def get_drive_rec(
    parent_folder_id: str,
    folders_db: DocDb,
    drives_db: DocDb,
    owner: str,
    headers: Dict[str, str],
):
    query = f"parent_folder_id={parent_folder_id}#1"
    drives = await drives_db.query(query_body=query, owner=owner, headers=headers)
    if drives["documents"]:
        return drives["documents"][0]["drive_id"]

    folders = await folders_db.query(query_body=query, owner=owner, headers=headers)
    if folders["documents"]:
        return folders["documents"][0]["drive_id"]

    raise HTTPException(status_code=404, detail="Drive not found")


async def get_group_from_drive(
    user: Dict[str, Any], drive_id: str, doc_dbs: Any, headers
) -> str:
    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("drive_id", drive_id, groups, doc_dbs.drives_db, headers),
        get_group("drive_id", drive_id, groups, doc_dbs.deleted_db, headers),
    )
    return group_id0 or group_id1


async def get_group_from_folder(
    user: Dict[str, Any], folder_id: str, doc_dbs: Any, headers: Dict[str, str]
) -> str:
    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("folder_id", folder_id, groups, doc_dbs.folders_db, headers),
        get_group("entity_id", folder_id, groups, doc_dbs.deleted_db, headers),
    )
    return group_id0 or group_id1


async def get_group_from_item(
    user: Dict[str, Any], item_id: str, doc_dbs: Any, headers
) -> str:
    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("folder_id", item_id, groups, doc_dbs.items_db, headers),
        get_group("entity_id", item_id, groups, doc_dbs.deleted_db, headers),
    )
    return group_id0 or group_id1


async def db_get(docdb: DocDb, partition_keys: Dict[str, Any], context: Context):
    async with context.start(
        action="db_get",
    ) as ctx:  # type: Context
        await ctx.info(text="partition_keys", data=partition_keys)
        asset = await docdb.get_document(
            partition_keys=partition_keys,
            clustering_keys={},
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )
        return asset


async def db_post(docdb: DocDb, doc: Any, context: Context):
    async with context.start(
        action="db_post", with_attributes={"groupId": doc["group_id"]}
    ) as ctx:  # type: Context
        return await docdb.update_document(
            doc, owner=Constants.public_owner, headers=ctx.headers()
        )


async def db_query(
    docdb: DocDb, key: str, value: str, max_count: int, context: Context
):
    async with context.start(action="db_query") as ctx:  # type: Context
        r = await docdb.query(
            query_body=f"{key}={value}#{max_count}",
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )

        return list(r["documents"])


async def db_delete(docdb: DocDb, doc: Dict[str, Any], context: Context):
    async with context.start(action="db_delete") as ctx:  # type: Context
        return await docdb.delete_document(
            doc=doc, owner=Constants.public_owner, headers=ctx.headers()
        )


async def get_parent(parent_id: str, configuration: Configuration, context: Context):
    folders_db, drives_db = (
        configuration.doc_dbs.folders_db,
        configuration.doc_dbs.drives_db,
    )
    parent_folder, parent_drive = await asyncio.gather(
        db_query(
            docdb=folders_db,
            key="folder_id",
            value=parent_id,
            max_count=1,
            context=context,
        ),
        db_query(
            docdb=drives_db,
            key="drive_id",
            value=parent_id,
            max_count=1,
            context=context,
        ),
    )
    if len(parent_folder) + len(parent_drive) == 0:
        raise HTTPException(status_code=404, detail="Containing drive/folder not found")
    parent = (parent_folder + parent_drive)[0]
    return parent
