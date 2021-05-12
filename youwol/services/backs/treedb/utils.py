import base64
from typing import Union, Mapping, List, Dict, Any, TypeVar

from fastapi import HTTPException
from starlette.requests import Request

from youwol_utils import (
    DocDb, get_all_individual_groups, asyncio, ensure_group_permission, generate_headers_downstream, user_info,
    get_user_group_ids,
    )
from .configurations import Configuration


async def init_resources(
        config: Configuration
        ):

    print("Ensure database resources")
    headers = await config.admin_headers if config.admin_headers else {}
    doc_dbs = config.doc_dbs
    items_ok = await doc_dbs.items_db.ensure_table(headers=headers)
    folders_ok = await doc_dbs.folders_db.ensure_table(headers=headers)
    drives_ok = await doc_dbs.drives_db.ensure_table(headers=headers)
    deleted_ok = await doc_dbs.deleted_db.ensure_table(headers=headers)

    if not (items_ok and folders_ok and drives_ok and deleted_ok):
        raise Exception(f"Problem during docdb's table initialisation {[items_ok, folders_ok, drives_ok, deleted_ok]}")

    print("resources initialization done")


def to_group_id(
        group_path: Union[str, None]
        ) -> str:

    if group_path == 'private' or group_path is None:
        return 'private'
    b = str.encode(group_path)
    return base64.urlsafe_b64encode(b).decode()


def to_owner(
        group_id: str
        ) -> Union[str, None]:

    if group_id == 'private':
        return None
    b = str.encode(group_id)
    return base64.urlsafe_b64decode(b).decode()


async def get_group(
        primary_key: str,
        primary_value: Union[str, float, int, bool],
        groups: List[str],
        doc_db: DocDb,
        headers: Mapping[str, str]
        ):

    requests = [doc_db.query(query_body=f"{primary_key}=${primary_value}#1", owner=group, headers=headers)
                for group in groups]

    responses = await asyncio.gather(*requests)
    group = next((g for i, g in enumerate(groups) if responses[i]["documents"]), -1)
    return group


def convert_out(d):
    to_convert = {
        "related_id": "relatedId",
        "drive_id": "driveId",
        "folder_id": "folderId",
        "group_id": "groupId",
        "item_id": "itemId",
        "entity_id": "entityId",
        "parent_folder_id": "parentFolderId",
        "bucket_path": "bucketPath"
        }
    r = {}
    for key, value in d.items():
        if key in to_convert:
            r[to_convert[key]] = value
        else:
            r[key] = value
    return r


def convert_in(d):
    to_convert = {
        "relatedId": "related_id",
        "driveId": "drive_id",
        "folderId": "folder_id",
        "groupId": "group_id",
        "itemId": "item_id",
        "entityId": "entity_id",
        "parentFolderId": "parent_folder_id",
        "bucketPath": "bucket_path"
        }
    r = {}
    for key, value in d.items():
        if key in to_convert:
            r[to_convert[key]] = value
        else:
            r[key] = value
    return r


async def ensure_drive(
        drive_id: str,
        group_id: str,
        docdb_drive: DocDb,
        headers: Dict[str, Any]
        ):

    try:
        await docdb_drive.get_document(partition_keys={"drive_id": drive_id}, clustering_keys={}, owner=group_id,
                                       headers=headers)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Drive not found")
        raise e


async def ensure_folder(
        folder_id: str,
        group_id: str,
        docdb_folder: DocDb,
        headers: Dict[str, Any]
        ):
    try:
        await docdb_folder.get_document(partition_keys={"folder_id": folder_id}, clustering_keys={}, owner=group_id,
                                        headers=headers)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Folder not found")
        raise e


def delete_folder(
        folder_id: str,
        group_id: str,
        docdb_folders: DocDb,
        headers: Dict[str, Any]
        ):
    return docdb_folders.delete_document(doc={"folder_id": folder_id}, owner=group_id, headers=headers)


def delete_item(
        item_id: str,
        group_id: str,
        docdb_items: DocDb,
        headers: Dict[str, Any]
        ):
    return docdb_items.delete_document(doc={"item_id": item_id}, owner=group_id, headers=headers)


async def get_drive_rec(
        parent_folder_id: str,
        folders_db: DocDb,
        drives_db: DocDb,
        owner: str,
        headers: Dict[str, str]
        ):

    query = f"parent_folder_id={parent_folder_id}#1"
    drives = await drives_db.query(query_body=query, owner=owner, headers=headers)
    if drives['documents']:
        return drives['documents'][0]['drive_id']

    folders = await folders_db.query(query_body=query, owner=owner, headers=headers)
    if folders['documents']:
        return folders['documents'][0]['drive_id']

    raise HTTPException(status_code=404, detail="Drive not found")


async def get_group_from_drive(
        user: Dict[str, Any],
        drive_id: str,
        doc_dbs: Any,
        headers) -> str:

    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("drive_id", drive_id, groups, doc_dbs.drives_db, headers),
        get_group("drive_id", drive_id, groups, doc_dbs.deleted_db, headers)
        )
    return group_id0 or group_id1


async def get_group_from_folder(
        user: Dict[str, Any],
        folder_id: str,
        doc_dbs: Any,
        headers: Dict[str, str]
        ) -> str:

    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("folder_id", folder_id, groups, doc_dbs.folders_db, headers),
        get_group("entity_id", folder_id, groups, doc_dbs.deleted_db, headers)
        )
    return group_id0 or group_id1


async def get_group_from_item(
        user: Dict[str, Any],
        item_id: str,
        doc_dbs: Any,
        headers
        ) -> str:

    groups = get_all_individual_groups(user["memberof"])
    group_id0, group_id1 = await asyncio.gather(
        get_group("folder_id", item_id, groups, doc_dbs.items_db, headers),
        get_group("entity_id", item_id, groups, doc_dbs.deleted_db, headers)
        )
    return group_id0 or group_id1


async def ensure_get_permission(
        request: Request,
        docdb: DocDb,
        partition_keys: Dict[str, Any],
        configuration: Configuration
        ):

    headers = generate_headers_downstream(request.headers)
    asset = await docdb.get_document(partition_keys=partition_keys, clustering_keys={},
                                     owner=configuration.public_owner, headers=headers)
    # there is no restriction on access asset 'metadata' for now
    ensure_group_permission(request=request, group_id=asset["group_id"])
    return asset


async def ensure_post_permission(
        request: Request,
        docdb: DocDb,
        doc: Any,
        configuration: Configuration
        ):

    ensure_group_permission(request=request, group_id=doc["group_id"])
    headers = generate_headers_downstream(request.headers)
    return await docdb.update_document(doc, owner=configuration.public_owner, headers=headers)


async def ensure_query_permission(
        request: Request,
        docdb: DocDb,
        key: str,
        value: str,
        max_count: int,
        configuration: Configuration
        ):

    headers = generate_headers_downstream(request.headers)
    user = user_info(request)
    allowed_groups = get_user_group_ids(user)
    r = await docdb.query(query_body=f"{key}={value}#{max_count}", owner=configuration.public_owner, headers=headers)

    return [d for d in r["documents"] if d['group_id'] in allowed_groups]


async def ensure_delete_permission(
        request: Request,
        docdb: DocDb,
        doc: Dict[str, Any],
        configuration: Configuration
        ):
    # only owning group can delete
    # if isinstance(doc, FolderResponse) or isinstance(doc, ItemResponse) or isinstance(doc, DriveResponse):
    doc = convert_in(doc)

    ensure_group_permission(request=request, group_id=doc["group_id"])

    headers = generate_headers_downstream(request.headers)
    return await docdb.delete_document(doc=doc, owner=configuration.public_owner, headers=headers)


async def get_parent(
        request: Request,
        parent_id: str,
        configuration: Configuration
        ):

    folders_db, drives_db = configuration.doc_dbs.folders_db, configuration.doc_dbs.drives_db
    parent_folder, parent_drive = await asyncio.gather(
        ensure_query_permission(request=request, docdb=folders_db, key="folder_id", value=parent_id,
                                configuration=configuration, max_count=1),
        ensure_query_permission(request=request, docdb=drives_db, key="drive_id", value=parent_id,
                                configuration=configuration, max_count=1)
        )
    if len(parent_folder) + len(parent_drive) == 0:
        raise HTTPException(status_code=404, detail="Containing drive/folder not found")
    parent = (parent_folder + parent_drive)[0]
    return parent
