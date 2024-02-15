# standard library
import base64
import json
import uuid

from collections.abc import Mapping

# typing
from typing import Any

# third parties
from fastapi import Depends, HTTPException
from starlette.requests import Request

# Youwol utilities
from youwol.utils import DocDb, asyncio, decode_id, get_all_individual_groups
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    ChildrenResponse,
    DefaultDriveResponse,
    DriveBody,
    DriveResponse,
    FolderBody,
    FolderResponse,
    ItemResponse,
)

# relative
from .configurations import Configuration, Constants, get_configuration


def to_group_id(group_path: str | None) -> str:
    if group_path == "private" or group_path is None:
        return "private"
    b = str.encode(group_path)
    return base64.urlsafe_b64encode(b).decode()


def to_owner(group_id: str) -> str | None:
    if group_id == "private":
        return None
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()


async def get_group(
    primary_key: str,
    primary_value: str | float | int | bool,
    groups: list[str],
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
    drive_id: str, group_id: str, docdb_drive: DocDb, headers: dict[str, Any]
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


def delete_folder(
    folder_id: str, group_id: str, docdb_folders: DocDb, headers: dict[str, Any]
):
    return docdb_folders.delete_document(
        doc={"folder_id": folder_id}, owner=group_id, headers=headers
    )


def delete_item(
    item_id: str, group_id: str, docdb_items: DocDb, headers: dict[str, Any]
):
    return docdb_items.delete_document(
        doc={"item_id": item_id}, owner=group_id, headers=headers
    )


async def get_drive_rec(
    parent_folder_id: str,
    folders_db: DocDb,
    drives_db: DocDb,
    owner: str,
    headers: dict[str, str],
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
    user: dict[str, Any], drive_id: str, doc_dbs: Any, headers
) -> str:
    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("drive_id", drive_id, groups, doc_dbs.drives_db, headers),
        get_group("drive_id", drive_id, groups, doc_dbs.deleted_db, headers),
    )
    return group_id0 or group_id1


async def get_group_from_folder(
    user: dict[str, Any], folder_id: str, doc_dbs: Any, headers: dict[str, str]
) -> str:
    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("folder_id", folder_id, groups, doc_dbs.folders_db, headers),
        get_group("entity_id", folder_id, groups, doc_dbs.deleted_db, headers),
    )
    return group_id0 or group_id1


async def get_group_from_item(
    user: dict[str, Any], item_id: str, doc_dbs: Any, headers
) -> str:
    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("folder_id", item_id, groups, doc_dbs.items_db, headers),
        get_group("entity_id", item_id, groups, doc_dbs.deleted_db, headers),
    )
    return group_id0 or group_id1


async def db_get(docdb: DocDb, partition_keys: dict[str, Any], context: Context):
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


async def db_delete(docdb: DocDb, doc: dict[str, Any], context: Context):
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


async def entities_children(
    folder_id: str, configuration: Configuration, context: Context
):
    # max_count: see comment in class 'Constants'
    max_count = Constants.max_children_count
    async with context.start(action="_children") as ctx:  # type: Context
        folders_db, items_db = (
            configuration.doc_dbs.folders_db,
            configuration.doc_dbs.items_db,
        )
        folders, items = await asyncio.gather(
            db_query(
                docdb=folders_db,
                key="parent_folder_id",
                value=folder_id,
                max_count=max_count,
                context=ctx,
            ),
            db_query(
                docdb=items_db,
                key="folder_id",
                value=folder_id,
                max_count=max_count,
                context=ctx,
            ),
        )

        return ChildrenResponse(
            folders=[doc_to_folder(f) for f in folders],
            items=[doc_to_item(f) for f in items],
        )


async def get_folder(folder_id: str, configuration: Configuration, context: Context):
    async with context.start(action="_get_folder") as ctx:
        doc = await db_get(
            partition_keys={"folder_id": folder_id},
            context=ctx,
            docdb=configuration.doc_dbs.folders_db,
        )
        return doc_to_folder(doc)


async def get_drive(drive_id: str, configuration: Configuration, context: Context):
    async with context.start(action="_get_drive") as ctx:
        docdb = configuration.doc_dbs.drives_db
        doc = await db_get(
            docdb=docdb, partition_keys={"drive_id": drive_id}, context=ctx
        )

        return DriveResponse(
            driveId=drive_id,
            name=doc["name"],
            metadata=doc["metadata"],
            groupId=doc["group_id"],
        )


async def get_folders_rec(
    folder_id: str, drive_id: str, configuration: Configuration, context: Context
):
    drive = await get_drive(
        drive_id=drive_id, configuration=configuration, context=context
    )

    folders = [
        await get_folder(
            folder_id=folder_id, configuration=configuration, context=context
        )
    ]
    while folders[0].parentFolderId != folders[0].driveId:
        folders = [
            await get_folder(
                folder_id=folders[0].parentFolderId,
                configuration=configuration,
                context=context,
            )
        ] + folders
    return folders, drive


async def list_deleted(drive_id: str, configuration: Configuration, context: Context):
    async with context.start("_list_deleted") as ctx:  # type: Context
        doc_dbs = configuration.doc_dbs
        entities = await doc_dbs.deleted_db.query(
            query_body=f"drive_id={drive_id}#100",
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )

        folders = [
            doc_to_folder(f, {"folder_id": f["deleted_id"]})
            for f in entities["documents"]
            if f["kind"] == "folder"
        ]

        items = [
            doc_to_item(
                f, {"item_id": f["deleted_id"], "folder_id": f["parent_folder_id"]}
            )
            for f in entities["documents"]
            if f["kind"] == "item"
        ]

        response = ChildrenResponse(folders=folders, items=items)
        return response


async def create_folder(
    parent_folder_id: str,
    folder: FolderBody,
    configuration: Configuration,
    context: Context,
):
    async with context.start(action="_create_folder") as ctx:  # type: Context
        folders_db, _ = (
            configuration.doc_dbs.folders_db,
            configuration.doc_dbs.drives_db,
        )
        parent = await get_parent(
            parent_id=parent_folder_id, configuration=configuration, context=ctx
        )

        doc = {
            "folder_id": folder.folderId or str(uuid.uuid4()),
            "name": folder.name,
            "parent_folder_id": parent_folder_id,
            "group_id": parent["group_id"],
            "type": folder.kind,
            "metadata": folder.metadata,
            "drive_id": parent["drive_id"],
        }
        await db_post(docdb=folders_db, doc=doc, context=ctx)

        response = doc_to_folder(doc)
        return response


async def create_drive(
    group_id: str, drive: DriveBody, configuration: Configuration, context: Context
):
    async with context.start(action="_create_drive") as ctx:  # type: Context
        docdb = configuration.doc_dbs.drives_db
        doc = {
            "name": drive.name,
            "drive_id": drive.driveId or str(uuid.uuid4()),
            "group_id": group_id,
            "metadata": drive.metadata,
        }

        await db_post(docdb=docdb, doc=doc, context=ctx)
        response = doc_to_drive_response(doc)
        return response


async def get_default_drive(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> DefaultDriveResponse:
    async with Context.start_ep(
        request=request,
        action="get default drive",
        with_attributes={"group_id": group_id},
    ) as ctx:
        default_drive_id = f"{group_id}_default-drive"
        try:
            await get_drive(
                drive_id=default_drive_id, configuration=configuration, context=ctx
            )
        except HTTPException as e_drive:
            if e_drive.status_code != 404:
                raise e_drive
            await ctx.warning("Default drive does not exist yet, start creation")
            await create_drive(
                group_id=group_id,
                drive=DriveBody(name="Default drive", driveId=default_drive_id),
                configuration=configuration,
                context=ctx,
            )

        download, home, system = await asyncio.gather(
            _ensure_folder(
                name="Download",
                folder_id=f"{default_drive_id}_download",
                parent_folder_id=default_drive_id,
                configuration=configuration,
                context=ctx,
            ),
            _ensure_folder(
                name="Home",
                folder_id=f"{default_drive_id}_home",
                parent_folder_id=default_drive_id,
                configuration=configuration,
                context=ctx,
            ),
            _ensure_folder(
                name="System",
                folder_id=f"{default_drive_id}_system",
                parent_folder_id=default_drive_id,
                configuration=configuration,
                context=ctx,
            ),
        )

        system_packages, system_tmp = await asyncio.gather(
            _ensure_folder(
                name="Packages",
                folder_id=f"{default_drive_id}_system_packages",
                parent_folder_id=system.folderId,
                configuration=configuration,
                context=ctx,
            ),
            _ensure_folder(
                name="Tmp",
                folder_id=f"{default_drive_id}_system_tmp",
                parent_folder_id=system.folderId,
                configuration=configuration,
                context=ctx,
            ),
        )

        resp = DefaultDriveResponse(
            groupId=group_id,
            driveId=default_drive_id,
            driveName="Default drive",
            downloadFolderId=download.folderId,
            downloadFolderName=download.name,
            homeFolderId=home.folderId,
            homeFolderName=home.name,
            tmpFolderId=system_tmp.folderId,
            tmpFolderName=system_tmp.name,
            systemFolderId=system.folderId,
            systemFolderName=system.name,
            systemPackagesFolderId=system_packages.folderId,
            systemPackagesFolderName=system_packages.name,
        )
        await ctx.info("Response", data=resp)
        return resp


async def _ensure_folder(
    name: str,
    folder_id: str,
    parent_folder_id: str,
    configuration: Configuration,
    context: Context,
):
    async with context.start(
        action="ensure folder", with_attributes={"folder_id": folder_id, "name": name}
    ) as ctx:
        try:
            folder_resp = await get_folder(
                folder_id=folder_id, configuration=configuration, context=context
            )
            await ctx.info("Folder already exists")
            return folder_resp
        except HTTPException as e_folder:
            if e_folder.status_code != 404:
                raise e_folder
            await ctx.warning("Folder does not exist yet, start creation")
            return await create_folder(
                parent_folder_id=parent_folder_id,
                folder=FolderBody(name=name, folderId=folder_id),
                configuration=configuration,
                context=ctx,
            )
