
import asyncio
import itertools
import uuid
from typing import Set, Tuple, List, Coroutine

from fastapi import HTTPException, APIRouter, Depends
from fastapi import Query as QueryParam

from starlette.requests import Request

from .configurations import Configuration, get_configuration
from .models import (
    GroupsResponse, Group, DriveResponse, DriveBody, DrivesResponse, RenameBody,
    FolderResponse, FolderBody, ItemResponse, ItemBody, ItemsResponse, MoveResponse, MoveItemBody, EntityResponse,
    ChildrenResponse, PurgeResponse, GetRecordsBody,
    )
from .utils import (
    ensure_post_permission, convert_out, ensure_get_permission, get_parent,
    ensure_query_permission, ensure_delete_permission,
    )
from youwol_utils import (
    user_info, get_all_individual_groups, private_group_id, to_group_id,
    generate_headers_downstream, ensure_group_permission, RecordsResponse, RecordsTable, RecordsKeyspace, RecordsDocDb,
    RecordsStorage,
    )

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "treedb-backend ok"}


@router.get("/groups",
            response_model=GroupsResponse,
            summary="list subscribed groups")
async def get_groups(request: Request):

    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    groups = [Group(id=private_group_id(user), path="private")] + \
             [Group(id=str(to_group_id(g)), path=g) for g in groups if g]

    return GroupsResponse(groups=groups)


@router.put("/groups/{group_id}/drives",
            summary="create a drive",
            response_model=DriveResponse)
async def create_drive(
        request: Request,
        group_id: str,
        drive: DriveBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    docdb = configuration.doc_dbs.drives_db
    doc = {"name": drive.name,
           "drive_id":  drive.driveId or str(uuid.uuid4()),
           "group_id": group_id,
           "metadata": drive.metadata}

    await ensure_post_permission(request=request, docdb=docdb, doc=doc, configuration=configuration)
    return DriveResponse(**convert_out(doc))


@router.get("/groups/{group_id}/drives",
            summary="list drives",
            response_model=DrivesResponse)
async def list_drives(
        request: Request,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    ensure_group_permission(request=request, group_id=group_id)

    docdb_drive = configuration.doc_dbs.drives_db
    drives = await docdb_drive.query(query_body=f"group_id={group_id}#100", owner=configuration.public_owner,
                                     headers=headers)

    drives = [DriveResponse(**convert_out(d)) for d in drives["documents"]]

    return DrivesResponse(drives=drives)


@router.post("/drives/{drive_id}",
             summary="update a drive",
             response_model=DriveResponse)
async def update_drive(
        request: Request,
        drive_id: str,
        body: RenameBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    docdb = configuration.doc_dbs.drives_db
    doc = await ensure_get_permission(request=request, docdb=docdb, partition_keys={'drive_id': drive_id},
                                      configuration=configuration)

    doc = {**doc, **{"name": body.name}}
    await ensure_post_permission(request=request, docdb=docdb, doc=doc, configuration=configuration)

    return DriveResponse(driveId=drive_id, name=body.name, metadata=doc["metadata"], groupId=doc['group_id'])


@router.get("/drives/{drive_id}",
            summary="get a drive",
            response_model=DriveResponse)
async def get_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    docdb = configuration.doc_dbs.drives_db
    doc = await ensure_get_permission(request=request, docdb=docdb, partition_keys={'drive_id': drive_id},
                                      configuration=configuration)

    return DriveResponse(driveId=drive_id, name=doc['name'], metadata=doc["metadata"], groupId=doc['group_id'])


@router.put("/folders/{parent_folder_id}",
            summary="create a folder",
            response_model=FolderResponse)
async def create_folder(
        request: Request,
        parent_folder_id: str,
        folder: FolderBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    folders_db, drives_db = configuration.doc_dbs.folders_db, configuration.doc_dbs.drives_db
    parent = await get_parent(request=request, parent_id=parent_folder_id, configuration=configuration)

    doc = {"folder_id": folder.folderId or str(uuid.uuid4()),
           "name":  folder.name,
           "parent_folder_id": parent_folder_id,
           "group_id": parent['group_id'],
           "type": folder.type,
           "metadata": folder.metadata,
           "drive_id": parent['drive_id']}
    await ensure_post_permission(request=request, docdb=folders_db, doc=doc, configuration=configuration)

    return FolderResponse(**convert_out(doc))


@router.post("/folders/{folder_id}",
             summary="update a folder",
             response_model=FolderResponse)
async def update_folder(
        request: Request,
        folder_id: str,
        body: RenameBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    folders_db = configuration.doc_dbs.folders_db
    doc = await ensure_get_permission(request=request, partition_keys={'folder_id': folder_id}, docdb=folders_db,
                                      configuration=configuration)
    doc = {**doc, **{"name": body.name}}
    await ensure_post_permission(request=request, docdb=folders_db, doc=doc, configuration=configuration)

    return FolderResponse(**convert_out(doc))


@router.get("/folders/{folder_id}",
            summary="get a folder",
            response_model=FolderResponse)
async def get_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    doc = await ensure_get_permission(request=request, partition_keys={'folder_id': folder_id},
                                      docdb=configuration.doc_dbs.folders_db, configuration=configuration)
    return FolderResponse(**convert_out(doc))


@router.put("/folders/{folder_id}/items",
            summary="create an item",
            response_model=ItemResponse)
async def create_item(
        request: Request,
        folder_id: str,
        item: ItemBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    items_db = configuration.doc_dbs.items_db
    parent = await get_parent(request=request, parent_id=folder_id, configuration=configuration)

    doc = {"item_id":  item.itemId or str(uuid.uuid4()),
           "folder_id": folder_id,
           "related_id": item.relatedId,
           "name":  item.name,
           "type": item.type,
           "group_id": parent["group_id"],
           "drive_id": parent['drive_id'],
           "metadata": item.metadata
           }
    await ensure_post_permission(request=request, docdb=items_db, doc=doc, configuration=configuration)

    return ItemResponse(**convert_out(doc))


@router.post("/items/{item_id}",
             summary="update an item",
             response_model=ItemResponse)
async def update_item(
        request: Request,
        item_id: str,
        body: RenameBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    items_db = configuration.doc_dbs.items_db
    doc = await ensure_get_permission(request=request, partition_keys={'item_id': item_id}, docdb=items_db,
                                      configuration=configuration)
    doc = {**doc, **{"name": body.name}}
    await ensure_post_permission(request=request, docdb=items_db, doc=doc, configuration=configuration)

    return ItemResponse(**convert_out(doc))


@router.get("/items/{item_id}",
            summary="get an item",
            response_model=ItemResponse)
async def get_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)):

    items_db = configuration.doc_dbs.items_db
    doc = await ensure_get_permission(request=request, partition_keys={'item_id': item_id}, docdb=items_db,
                                      configuration=configuration)
    return ItemResponse(**convert_out(doc))


@router.get("/items/from-related/{related_id}",
            summary="get an item",
            response_model=ItemsResponse)
async def get_items_by_related_id(
        request: Request,
        related_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    docdb = configuration.doc_dbs.items_db
    items = await ensure_query_permission(request=request, docdb=docdb, key="related_id", value=related_id,
                                          max_count=100, configuration=configuration)

    return ItemsResponse(items=[ItemResponse(**convert_out(item)) for item in items])


@router.post("/move",
             response_model=MoveResponse,
             summary="move an item")
async def move(
        request: Request,
        body: MoveItemBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    items_db = configuration.doc_dbs.items_db
    folders_db = configuration.doc_dbs.folders_db

    items, folders, to_folder_drive = await asyncio.gather(
        ensure_query_permission(request=request, docdb=items_db, key="item_id", value=body.targetId, max_count=1,
                                configuration=configuration),
        ensure_query_permission(request=request, docdb=folders_db, key="folder_id", value=body.targetId, max_count=1,
                                configuration=configuration),
        get_entity(request=request, entity_id=body.destinationFolderId, include_items=False,
                   configuration=configuration)
        # ensure_get_permission(request=request, docdb=folders_db, primary_key=body.destinationFolderId),
        )
    if len(items) + len(folders) == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    destination = to_folder_drive.entity
    destination_id = destination.folderId if isinstance(destination, FolderResponse) else destination.driveId
    target = items[0] if len(items) > 0 else folders[0]

    if 'parent_folder_id' in target:
        doc = {**target, **{"parent_folder_id": destination_id,
                            "group_id": destination.groupId,
                            "drive_id": destination.driveId}}
        await ensure_post_permission(request=request, docdb=folders_db, doc=doc, configuration=configuration)
        if target['drive_id'] == destination.driveId and \
                target['group_id'] == destination.groupId:
            return MoveResponse(
                foldersCount=1,
                items=[]
                )
        to_move = await children(request=request, folder_id=target['folder_id'], configuration=configuration)

        bodies = [MoveItemBody(targetId=item.itemId, destinationFolderId=target['folder_id'])
                  for item in to_move.items] + \
                 [MoveItemBody(targetId=item.folderId, destinationFolderId=target['folder_id'])
                  for item in to_move.folders]

        results = await asyncio.gather(*[
            move(request=request, body=body, configuration=configuration) for body in bodies
            ])
        all_items = list(flatten([r.items for r in results]))
        return MoveResponse(
            foldersCount=1 + sum([r.foldersCount for r in results]),
            items=all_items
            )

    doc = {**target,
           **{"folder_id": destination_id,
              "group_id": destination.groupId,
              "drive_id": destination.driveId}
           }
    await ensure_post_permission(request=request, docdb=items_db, doc=doc, configuration=configuration)
    return MoveResponse(foldersCount=0, items=[convert_out(doc)])


@router.get("/entities/{entity_id}",
            response_model=EntityResponse,
            summary="get an entity from id in [item, folder, drive]"
            )
async def get_entity(
        request: Request, entity_id: str,
        include_drives: bool = QueryParam(True, alias="include-drives"),
        include_folders: bool = QueryParam(True, alias="include-folders"),
        include_items: bool = QueryParam(True, alias="include-items"),
        configuration: Configuration = Depends(get_configuration)
        ):

    items_db, folders_db, drives_db = configuration.doc_dbs.items_db,  configuration.doc_dbs.folders_db, \
                                      configuration.doc_dbs.drives_db

    drive = ensure_query_permission(request=request, docdb=drives_db, key="drive_id", value=entity_id, max_count=1,
                                    configuration=configuration) if include_drives else None
    folder = ensure_query_permission(request=request, docdb=folders_db, key="folder_id", value=entity_id, max_count=1,
                                     configuration=configuration) if include_folders else None
    item = ensure_query_permission(request=request, docdb=items_db, key="item_id", value=entity_id, max_count=1,
                                   configuration=configuration) if include_items else None

    futures = [d for d in [item, folder, drive] if d]
    entities = list(flatten(await asyncio.gather(*futures)))
    if not entities:
        raise HTTPException(status_code=404, detail="No entities found with corresponding id")
    entity = entities[0]
    if 'item_id' in entity:
        return EntityResponse(entityType='item', entity=ItemResponse(**convert_out(entity)))

    if 'parent_folder_id' in entity:
        return EntityResponse(entityType='folder', entity=FolderResponse(**convert_out(entity)))

    return EntityResponse(entityType='drive', entity=DriveResponse(**convert_out(entity)))


@router.get("/folders/{folder_id}/children",
            summary="list drives",
            response_model=ChildrenResponse)
async def children(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)):

    folders_db, items_db = configuration.doc_dbs.folders_db, configuration.doc_dbs.items_db
    folders, items = await asyncio.gather(
        ensure_query_permission(request=request, docdb=folders_db, key="parent_folder_id", value=folder_id,
                                max_count=100, configuration=configuration),
        ensure_query_permission(request=request, docdb=items_db, key="folder_id", value=folder_id, max_count=100,
                                configuration=configuration)
        )

    return ChildrenResponse(folders=[FolderResponse(**convert_out(f)) for f in folders],
                            items=[ItemResponse(**convert_out(f)) for f in items])


@router.get("/drives/{drive_id}/deleted",
            summary="list items of the drive queued for deletion",
            response_model=ChildrenResponse)
async def list_deleted(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_dbs = configuration.doc_dbs
    entities = await doc_dbs.deleted_db.query(query_body=f"drive_id={drive_id}#100", owner=configuration.public_owner,
                                              headers=headers)

    folders = [FolderResponse(**{**convert_out(f), **{"folderId": f['deleted_id']}})
               for f in entities["documents"] if f['kind'] == 'folder']
    items = [ItemResponse(**{**convert_out(f), **{"itemId": f['deleted_id'], "folderId": f['parent_folder_id']}})
             for f in entities["documents"] if f['kind'] == 'item']

    return ChildrenResponse(folders=folders, items=items)


@router.delete("/items/{item_id}",
               summary="delete an entity")
async def queue_delete_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    dbs = configuration.doc_dbs
    items_db, folders_db, drives_db, deleted_db = dbs.items_db, dbs.folders_db, dbs.drives_db, dbs.deleted_db

    doc = await ensure_get_permission(request=request, partition_keys={'item_id': item_id}, docdb=items_db,
                                      configuration=configuration)

    doc = {"deleted_id": doc['item_id'], "drive_id": doc["drive_id"], "type": doc['type'],
           "kind": 'item', "related_id": doc["related_id"], "name": doc['name'], "parent_folder_id": doc["folder_id"],
           "group_id": doc["group_id"], "metadata": doc["metadata"]}

    deleted_db = configuration.doc_dbs.deleted_db
    await ensure_post_permission(request=request, doc=doc, docdb=deleted_db, configuration=configuration)
    await ensure_delete_permission(request=request, docdb=items_db,
                                   doc={"item_id": doc['deleted_id'], "group_id": doc["group_id"]},
                                   configuration=configuration)
    return {}


@router.delete("/folders/{folder_id}",
               summary="delete a folder and its content")
async def queue_delete_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)):

    dbs = configuration.doc_dbs
    folders_db, drives_db, deleted_db = dbs.folders_db, dbs.drives_db, dbs.deleted_db

    doc = await ensure_get_permission(request=request, partition_keys={'folder_id': folder_id}, docdb=folders_db,
                                      configuration=configuration)

    doc = {"deleted_id": doc['folder_id'], "drive_id": doc['drive_id'], "type": doc['type'], "kind": 'folder',
           "name": doc['name'], "parent_folder_id": doc["parent_folder_id"], "related_id": "",
           "group_id": doc["group_id"], "metadata": doc["metadata"]}

    deleted_db = configuration.doc_dbs.deleted_db

    await ensure_post_permission(request=request, doc=doc, docdb=deleted_db, configuration=configuration)
    await ensure_delete_permission(request=request, docdb=folders_db,
                                   doc={"folder_id": doc['deleted_id'], "group_id": doc["group_id"]},
                                   configuration=configuration)
    return {}


@router.delete("/drives/{drive_id}",
               summary="delete drive, need to be empty")
async def delete_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)):

    drives_db = configuration.doc_dbs.drives_db
    entities, deleted = await asyncio.gather(
        children(request=request, folder_id=drive_id, configuration=configuration),
        list_deleted(request=request, drive_id=drive_id, configuration=configuration)
        )

    if len(entities.folders + entities.items + deleted.items + deleted.folders) > 0:
        raise HTTPException(status_code=428, detail="the drive needs to be empty and purged before deletion")

    doc = await ensure_get_permission(request=request, partition_keys={'drive_id': drive_id}, docdb=drives_db,
                                      configuration=configuration)
    await ensure_delete_permission(request=request, docdb=drives_db, doc=doc, configuration=configuration)
    return {}


@router.delete("/drives/{drive_id}/purge",
               summary="purge drive's items scheduled for deletion",
               response_model=PurgeResponse)
async def purge_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    dbs = configuration.doc_dbs
    folders_db, items_db = dbs.folders_db, dbs.items_db

    deleted = await list_deleted(request=request, drive_id=drive_id, configuration=configuration)

    deletion_items = [ensure_delete_permission(request=request, docdb=items_db, doc=f.dict(),
                                               configuration=configuration)
                      for f in deleted.items]
    deletion_folders = [ensure_delete_permission(request=request, docdb=folders_db, doc=f.dict(),
                                                 configuration=configuration)
                        for f in deleted.folders]

    skip_items = {e.itemId for e in deleted.items}

    children_folder = [purge_folder(request=request, drive_id=drive_id, folder_id=f.folderId, skip_folders=set(),
                                    skip_items=skip_items, configuration=configuration)
                       for f in deleted.folders]

    deletion_children_folders = await asyncio.gather(*children_folder)

    deletion_rec_items = list(flatten([d for d, _, _ in deletion_children_folders]))
    deletion_rec_folders = list(flatten([d for _, d, _ in deletion_children_folders]))
    list_items = list(flatten([d for _, _, d in deletion_children_folders]))
    all_entities_delete = [*deletion_rec_items, *deletion_rec_folders, *deletion_items, *deletion_folders]

    await asyncio.gather(*all_entities_delete)

    deleted_db = configuration.doc_dbs.deleted_db
    deleted_db_items = await ensure_query_permission(request=request, docdb=deleted_db, key="drive_id", value=drive_id,
                                                     max_count=100, configuration=configuration)
    await asyncio.gather(*[
        ensure_delete_permission(request=request, docdb=deleted_db, doc=item,
                                 configuration=configuration)
        for item in deleted_db_items])

    return PurgeResponse(foldersCount=len(deletion_folders) + len(deletion_rec_folders),
                         itemsCount=len(deletion_items) + len(deletion_rec_items),
                         items=list_items + deleted.items
                         )


async def purge_folder(
        request: Request,
        drive_id: str,
        folder_id: str,
        skip_folders: Set[str],
        skip_items: Set[str],
        configuration: Configuration
        ) -> Tuple[List[Coroutine], List[Coroutine], List[ItemResponse]]:

    doc_dbs = configuration.doc_dbs
    content = await children(request=request, folder_id=folder_id, configuration=configuration)

    delete_items = [ensure_delete_permission(request=request, docdb=doc_dbs.items_db, doc=f.dict(),
                                             configuration=configuration)
                    for f in content.items if f.itemId not in skip_items]
    delete_folders = [ensure_delete_permission(request=request, docdb=doc_dbs.folders_db, doc=f.dict(),
                                               configuration=configuration)
                      for f in content.folders if f.folderId not in skip_items]

    skip_items = skip_items.union({f.itemId for f in content.items})

    children_folder = [purge_folder(request=request, drive_id=drive_id, folder_id=f.folderId, skip_folders=skip_folders,
                                    skip_items=skip_items, configuration=configuration)
                       for f in content.folders if f.folderId not in skip_folders]

    deletion_rec_folders = await asyncio.gather(*children_folder)

    return (delete_items + list(flatten([d for d, _, _ in deletion_rec_folders])),
            delete_folders + list(flatten([d for _, d, _ in deletion_rec_folders])),
            content.items + list(flatten([d for _, _, d in deletion_rec_folders])))


async def get_items_rec(request, folder_id: str, configuration: Configuration):

    resp = await children(request=request, folder_id=folder_id, configuration=configuration)

    children_folders = await asyncio.gather(*[
        get_items_rec(request=request, folder_id=folder.folderId, configuration=configuration)
        for folder in resp.folders
        ])

    folders = [folder.folderId for folder in resp.folders] + \
        list(flatten([[folder for folder in folders]
                      for items, folders in children_folders]))
    items = [item.itemId for item in resp.items] +\
        list(flatten([[item for item in items]
                      for items, folders in children_folders]))

    return items, folders


@router.post("/records",
             response_model=RecordsResponse,
             summary="get records")
async def get_records(
        request: Request,
        body: GetRecordsBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    items_db, folders_db, drives_db = configuration.doc_dbs.items_db, configuration.doc_dbs.folders_db, \
        configuration.doc_dbs.drives_db

    drives, folders = await asyncio.gather(
        ensure_query_permission(request=request, docdb=drives_db, key="drive_id", value=body.folderId, max_count=1,
                                configuration=configuration),
        ensure_query_permission(request=request, docdb=folders_db, key="folder_id", value=body.folderId, max_count=1,
                                configuration=configuration)
        )
    if len(drives) + len(folders) == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    entities = await get_items_rec(request=request, folder_id=body.folderId, configuration=configuration)

    table_items = RecordsTable(id=items_db.table_name, primaryKey=items_db.table_body.partition_key[0],
                               values=entities[0])
    table_folders = RecordsTable(id=folders_db.table_name, primaryKey=folders_db.table_body.partition_key[0],
                                 values=entities[1])

    group_id = to_group_id(configuration.public_owner)
    keyspace = RecordsKeyspace(id=items_db.keyspace_name, groupId=group_id, tables=[table_items, table_folders])

    response = RecordsResponse(docdb=RecordsDocDb(keyspaces=[keyspace]), storage=RecordsStorage(buckets=[]))

    return response
