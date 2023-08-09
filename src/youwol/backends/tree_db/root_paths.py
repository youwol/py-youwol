# standard library
import asyncio
import itertools
import json
import uuid

# typing
from typing import Coroutine, List, Optional, Set, Tuple, cast

# third parties
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from starlette.requests import Request

# Youwol backends
from youwol.backends.tree_db.configurations import (
    Configuration,
    Constants,
    get_configuration,
)
from youwol.backends.tree_db.utils import (
    db_delete,
    db_get,
    db_post,
    db_query,
    doc_to_drive_response,
    doc_to_folder,
    doc_to_item,
    folder_to_doc,
    get_parent,
    item_to_doc,
)

# Youwol utilities
from youwol.utils import (
    ensure_group_permission,
    get_all_individual_groups,
    private_group_id,
    to_group_id,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    BorrowBody,
    ChildrenResponse,
    DefaultDriveResponse,
    DriveBody,
    DriveResponse,
    DrivesResponse,
    EntityResponse,
    FolderBody,
    FolderResponse,
    Group,
    GroupsResponse,
    ItemBody,
    ItemResponse,
    ItemsResponse,
    MoveItemBody,
    MoveResponse,
    PathResponse,
    PurgeResponse,
    RenameBody,
)

router = APIRouter(tags=["treedb-backend"])
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "treedb-backend ok"}


@router.get("/groups", response_model=GroupsResponse, summary="list subscribed groups")
async def get_groups(request: Request):
    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    groups = [Group(id=private_group_id(user), path="private")] + [
        Group(id=str(to_group_id(g)), path=g) for g in groups if g
    ]

    return GroupsResponse(groups=groups)


async def _create_drive(
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


@router.put(
    "/groups/{group_id}/drives", summary="create a drive", response_model=DriveResponse
)
async def create_drive(
    request: Request,
    group_id: str,
    drive: DriveBody,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[DriveResponse] = None
    async with Context.start_ep(
        request=request, action="create drive", body=drive, response=lambda: response
    ) as ctx:  # type: Context
        response = await _create_drive(
            group_id=group_id, drive=drive, configuration=configuration, context=ctx
        )
        return response


@router.get(
    "/groups/{group_id}/drives", summary="list drives", response_model=DrivesResponse
)
async def list_drives(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[DrivesResponse] = None
    async with Context.start_ep(
        request=request,
        action="list_drives",
        with_attributes={"groupId": group_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        ensure_group_permission(request=request, group_id=group_id)

        docdb_drive = configuration.doc_dbs.drives_db
        drives = await docdb_drive.query(
            query_body=f"group_id={group_id}#100",
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )

        drives = [doc_to_drive_response(d) for d in drives["documents"]]

        response = DrivesResponse(drives=drives)
        return response


@router.post(
    "/drives/{drive_id}", summary="update a drive", response_model=DriveResponse
)
async def update_drive(
    request: Request,
    drive_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[DriveResponse] = None
    async with Context.start_ep(
        request=request,
        action="update_drive",
        body=body,
        with_attributes={"drive_id": drive_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        docdb = configuration.doc_dbs.drives_db
        doc = await db_get(
            docdb=docdb, partition_keys={"drive_id": drive_id}, context=ctx
        )

        doc = {**doc, **{"name": body.name}}
        await db_post(docdb=docdb, doc=doc, context=ctx)

        response = DriveResponse(
            driveId=drive_id,
            name=body.name,
            metadata=doc["metadata"],
            groupId=doc["group_id"],
        )
        return response


async def _get_drive(drive_id: str, configuration: Configuration, context: Context):
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


@router.get(
    "/default-drive",
    response_model=DefaultDriveResponse,
    summary="get user's default drive",
)
async def get_default_user_drive(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    user = user_info(request)
    return await get_default_drive(
        request=request, group_id=private_group_id(user), configuration=configuration
    )


@router.get("/drives/{drive_id}", summary="get a drive", response_model=DriveResponse)
async def get_drive(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[DriveResponse] = None
    async with Context.start_ep(
        request=request,
        action="get_drive",
        with_attributes={"drive_id": drive_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        response = await _get_drive(
            drive_id=drive_id, configuration=configuration, context=ctx
        )
        return response


async def ensure_folder(
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
            folder_resp = await _get_folder(
                folder_id=folder_id, configuration=configuration, context=context
            )
            await ctx.info("Folder already exists")
            return folder_resp
        except HTTPException as e_folder:
            if e_folder.status_code != 404:
                raise e_folder
            await ctx.warning("Folder does not exist yet, start creation")
            return await _create_folder(
                parent_folder_id=parent_folder_id,
                folder=FolderBody(name=name, folderId=folder_id),
                configuration=configuration,
                context=ctx,
            )


@router.get(
    "/groups/{group_id}/default-drive",
    response_model=DefaultDriveResponse,
    summary="get group's default drive",
)
async def get_default_drive(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request,
        action="get default drive",
        with_attributes={"group_id": group_id},
        muted_http_errors={404},
    ) as ctx:
        default_drive_id = f"{group_id}_default-drive"
        try:
            await _get_drive(
                drive_id=default_drive_id, configuration=configuration, context=ctx
            )
        except HTTPException as e_drive:
            if e_drive.status_code != 404:
                raise e_drive
            await ctx.warning("Default drive does not exist yet, start creation")
            await _create_drive(
                group_id=group_id,
                drive=DriveBody(name="Default drive", driveId=default_drive_id),
                configuration=configuration,
                context=ctx,
            )

        download, home, system = await asyncio.gather(
            ensure_folder(
                name="Download",
                folder_id=f"{default_drive_id}_download",
                parent_folder_id=default_drive_id,
                configuration=configuration,
                context=ctx,
            ),
            ensure_folder(
                name="Home",
                folder_id=f"{default_drive_id}_home",
                parent_folder_id=default_drive_id,
                configuration=configuration,
                context=ctx,
            ),
            ensure_folder(
                name="System",
                folder_id=f"{default_drive_id}_system",
                parent_folder_id=default_drive_id,
                configuration=configuration,
                context=ctx,
            ),
        )

        system_packages, system_tmp = await asyncio.gather(
            ensure_folder(
                name="Packages",
                folder_id=f"{default_drive_id}_system_packages",
                parent_folder_id=system.folderId,
                configuration=configuration,
                context=ctx,
            ),
            ensure_folder(
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


async def _create_folder(
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


@router.put(
    "/folders/{parent_folder_id}",
    summary="create a folder",
    response_model=FolderResponse,
)
async def create_folder(
    request: Request,
    parent_folder_id: str,
    folder: FolderBody,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[FolderResponse] = None
    async with Context.start_ep(
        request=request,
        action="create_folder",
        body=folder,
        with_attributes={"parent_folder_id": parent_folder_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        response = await _create_folder(
            parent_folder_id=parent_folder_id,
            folder=folder,
            configuration=configuration,
            context=ctx,
        )
        return response


@router.post(
    "/folders/{folder_id}", summary="update a folder", response_model=FolderResponse
)
async def update_folder(
    request: Request,
    folder_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[FolderResponse] = None
    async with Context.start_ep(
        request=request,
        action="update_folder",
        body=body,
        with_attributes={"folder_id": folder_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        folders_db = configuration.doc_dbs.folders_db
        doc = await db_get(
            partition_keys={"folder_id": folder_id}, docdb=folders_db, context=ctx
        )
        doc = {**doc, **{"name": body.name}}
        await db_post(docdb=folders_db, doc=doc, context=ctx)

        response = doc_to_folder(doc)
        return response


async def _get_folder(folder_id: str, configuration: Configuration, context: Context):
    async with context.start(action="_get_folder") as ctx:
        doc = await db_get(
            partition_keys={"folder_id": folder_id},
            context=ctx,
            docdb=configuration.doc_dbs.folders_db,
        )
        return doc_to_folder(doc)


@router.get(
    "/folders/{folder_id}", summary="get a folder", response_model=FolderResponse
)
async def get_folder(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[FolderResponse] = None
    async with Context.start_ep(
        request=request,
        action="get_folder",
        with_attributes={"folder_id": folder_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        response = await _get_folder(
            folder_id=folder_id, configuration=configuration, context=ctx
        )
        return response


async def _create_item(
    folder_id: str, item: ItemBody, configuration: Configuration, context: Context
):
    async with context.start(action="_create_item") as ctx:
        items_db = configuration.doc_dbs.items_db
        parent = await get_parent(
            parent_id=folder_id, configuration=configuration, context=ctx
        )

        doc = {
            "item_id": item.itemId or str(uuid.uuid4()),
            "folder_id": folder_id,
            "related_id": item.assetId,
            "name": item.name,
            "type": item.kind,
            "group_id": parent["group_id"],
            "drive_id": parent["drive_id"],
            "metadata": json.dumps({"borrowed": item.borrowed}),
        }
        await db_post(docdb=items_db, doc=doc, context=ctx)

        response = doc_to_item(doc)
        return response


@router.put(
    "/folders/{folder_id}/items", summary="create an item", response_model=ItemResponse
)
async def create_item(
    request: Request,
    folder_id: str,
    item: ItemBody,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[ItemResponse] = None
    async with Context.start_ep(
        request=request,
        action="create_item",
        body=item,
        with_attributes={"folder_id": folder_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        return await _create_item(
            folder_id=folder_id, item=item, configuration=configuration, context=ctx
        )


@router.post("/items/{item_id}", summary="update an item", response_model=ItemResponse)
async def update_item(
    request: Request,
    item_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[ItemResponse] = None
    async with Context.start_ep(
        request=request,
        action="update_item",
        body=body,
        with_attributes={"item_id": item_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        items_db = configuration.doc_dbs.items_db
        doc = await db_get(
            partition_keys={"item_id": item_id}, docdb=items_db, context=ctx
        )
        doc = {**doc, **{"name": body.name}}
        await db_post(docdb=items_db, doc=doc, context=ctx)

        response = doc_to_item(doc)
        return response


async def _get_item(item_id: str, configuration: Configuration, context: Context):
    async with context.start(action="_get_item") as ctx:  # type: Context
        items_db = configuration.doc_dbs.items_db
        doc = await db_get(
            partition_keys={"item_id": item_id}, docdb=items_db, context=ctx
        )
        return doc_to_item(doc)


@router.get("/items/{item_id}", summary="get an item", response_model=ItemResponse)
async def get_item(
    request: Request,
    item_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[ItemResponse] = None
    async with Context.start_ep(
        request=request,
        action="get_item",
        with_attributes={"item_id": item_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        response = await _get_item(
            item_id=item_id, configuration=configuration, context=ctx
        )
        return response


@router.get(
    "/items/from-asset/{asset_id}", summary="get an item", response_model=ItemsResponse
)
async def get_items_by_asset_id(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[ItemsResponse] = None
    async with Context.start_ep(
        request=request,
        action="get_item",
        with_attributes={"assetId": asset_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        docdb = configuration.doc_dbs.items_db
        items = await db_query(
            docdb=docdb, key="related_id", value=asset_id, max_count=100, context=ctx
        )

        response = ItemsResponse(items=[doc_to_item(item) for item in items])
        return response


async def get_folders_rec(
    folder_id: str, drive_id: str, configuration: Configuration, context: Context
):
    drive = await _get_drive(
        drive_id=drive_id, configuration=configuration, context=context
    )

    folders = [
        await _get_folder(
            folder_id=folder_id, configuration=configuration, context=context
        )
    ]
    while folders[0].parentFolderId != folders[0].driveId:
        folders = [
            await _get_folder(
                folder_id=folders[0].parentFolderId,
                configuration=configuration,
                context=context,
            )
        ] + folders
    return folders, drive


@router.get(
    "/items/{item_id}/path",
    summary="get the path of an item",
    response_model=PathResponse,
)
async def get_path(
    request: Request,
    item_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[PathResponse] = None
    async with Context.start_ep(
        request=request,
        action="get_path",
        with_attributes={"item_id": item_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        item = await _get_item(
            item_id=item_id, configuration=configuration, context=ctx
        )
        folders, drive = await get_folders_rec(
            folder_id=item.folderId,
            drive_id=item.driveId,
            configuration=configuration,
            context=ctx,
        )

        response = PathResponse(item=item, folders=folders, drive=drive)
        return response


@router.get(
    "/folders/{folder_id}/path",
    summary="get the path of a folder",
    response_model=PathResponse,
)
async def get_path_folder(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[PathResponse] = None
    async with Context.start_ep(
        request=request,
        action="get_path_folder",
        with_attributes={"folder_id": folder_id},
        response=lambda: response,
    ) as ctx:  # type: Context
        folder = await _get_folder(
            folder_id=folder_id, configuration=configuration, context=ctx
        )
        folders, drive = await get_folders_rec(
            folder_id=folder_id,
            drive_id=folder.driveId,
            configuration=configuration,
            context=ctx,
        )

        response = PathResponse(folders=folders, drive=drive)
        return response


@router.post("/move", response_model=MoveResponse, summary="move an item")
async def move(
    request: Request,
    body: MoveItemBody,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[MoveResponse] = None
    async with Context.start_ep(
        request=request, action="move", body=body, response=lambda: response
    ) as ctx:  # type: Context
        items_db = configuration.doc_dbs.items_db
        folders_db = configuration.doc_dbs.folders_db

        items, folders, to_folder_or_drive = await asyncio.gather(
            db_query(
                docdb=items_db,
                key="item_id",
                value=body.targetId,
                max_count=1,
                context=ctx,
            ),
            db_query(
                docdb=folders_db,
                key="folder_id",
                value=body.targetId,
                max_count=1,
                context=ctx,
            ),
            _get_entity(
                entity_id=body.destinationFolderId,
                include_items=False,
                configuration=configuration,
                context=ctx,
            ),
            return_exceptions=True,
        )
        if len(items) + len(folders) == 0:
            raise HTTPException(
                status_code=404, detail="Source item or folder not found in database"
            )

        if (
            isinstance(to_folder_or_drive, HTTPException)
            and to_folder_or_drive.status_code == 404
        ):
            raise HTTPException(
                status_code=404,
                detail="Destination folder or drive not found in database",
            )

        if isinstance(to_folder_or_drive, Exception):
            raise to_folder_or_drive

        to_folder_or_drive = cast(EntityResponse, to_folder_or_drive)
        destination = to_folder_or_drive.entity
        destination_id = (
            destination.folderId
            if isinstance(destination, FolderResponse)
            else destination.driveId
        )
        target = items[0] if len(items) > 0 else folders[0]

        if "parent_folder_id" in target:
            doc = {
                **target,
                **{
                    "parent_folder_id": destination_id,
                    "group_id": destination.groupId,
                    "drive_id": destination.driveId,
                },
            }
            await db_post(docdb=folders_db, doc=doc, context=ctx)
            if (
                target["drive_id"] == destination.driveId
                and target["group_id"] == destination.groupId
            ):
                return MoveResponse(foldersCount=1, items=[])
            to_move = await _children(
                folder_id=target["folder_id"], configuration=configuration, context=ctx
            )

            bodies = [
                MoveItemBody(
                    targetId=item.itemId, destinationFolderId=target["folder_id"]
                )
                for item in to_move.items
                # For now only 'original' assets can be moved (no 'symlinks'), related to change in authorisation policy
                # (handled by assets-gtw.treedb-backend)
                if not item.borrowed
            ] + [
                MoveItemBody(
                    targetId=item.folderId, destinationFolderId=target["folder_id"]
                )
                for item in to_move.folders
            ]

            results = await asyncio.gather(
                *[
                    move(request=request, body=body, configuration=configuration)
                    for body in bodies
                ]
            )
            all_items = list(flatten([r.items for r in results]))
            return MoveResponse(
                foldersCount=1 + sum(r.foldersCount for r in results), items=all_items
            )

        doc = {
            **target,
            **{
                "folder_id": destination_id,
                "group_id": destination.groupId,
                "drive_id": destination.driveId,
            },
        }
        await db_post(docdb=items_db, doc=doc, context=ctx)
        response = MoveResponse(foldersCount=0, items=[doc_to_item(doc)])
        return response


@router.post(
    "/items/{item_id}/borrow", response_model=ItemResponse, summary="borrow item"
)
async def borrow(
    request: Request,
    item_id: str,
    body: BorrowBody,
    configuration: Configuration = Depends(get_configuration),
):
    response = Optional[ItemResponse]

    async with Context.start_ep(
        request=request,
        action="borrow item",
        body=body,
        response=lambda: response,
        with_attributes={"item_id": item_id},
    ) as ctx:
        item = await _get_item(
            item_id=item_id, configuration=configuration, context=ctx
        )

        metadata = json.loads(item.metadata)
        metadata["borrowed"] = True
        item.itemId = body.targetId if body.targetId else str(uuid.uuid4())
        item.borrowed = True
        item.metadata = json.dumps(metadata)
        return await _create_item(
            folder_id=body.destinationFolderId,
            item=ItemBody(**item.dict()),
            configuration=configuration,
            context=ctx,
        )


async def _get_entity(
    entity_id: str,
    configuration: Configuration,
    context: Context,
    include_drives: bool = True,
    include_folders: bool = True,
    include_items: bool = True,
):
    async with context.start(action="_get_entity") as ctx:  # type: Context
        items_db, folders_db, drives_db = (
            configuration.doc_dbs.items_db,
            configuration.doc_dbs.folders_db,
            configuration.doc_dbs.drives_db,
        )

        drive = (
            db_query(
                docdb=drives_db,
                key="drive_id",
                value=entity_id,
                max_count=1,
                context=ctx,
            )
            if include_drives
            else None
        )
        folder = (
            db_query(
                docdb=folders_db,
                key="folder_id",
                value=entity_id,
                max_count=1,
                context=ctx,
            )
            if include_folders
            else None
        )
        item = (
            db_query(
                docdb=items_db, key="item_id", value=entity_id, max_count=1, context=ctx
            )
            if include_items
            else None
        )

        futures = [d for d in [item, folder, drive] if d]
        entities = list(flatten(await asyncio.gather(*futures)))
        if not entities:
            raise HTTPException(
                status_code=404, detail="No entities found with corresponding id"
            )
        entity = entities[0]
        if "item_id" in entity:
            return EntityResponse(entityType="item", entity=doc_to_item(entity))

        if "parent_folder_id" in entity:
            return EntityResponse(entityType="folder", entity=doc_to_folder(entity))

        return EntityResponse(entityType="drive", entity=doc_to_drive_response(entity))


@router.get(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    summary="get an entity from id in [item, folder, drive]",
)
async def get_entity(
    request: Request,
    entity_id: str,
    include_drives: bool = QueryParam(True, alias="include-drives"),
    include_folders: bool = QueryParam(True, alias="include-folders"),
    include_items: bool = QueryParam(True, alias="include-items"),
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[EntityResponse] = None
    async with Context.start_ep(
        request=request, action="get_entity", response=lambda: response
    ) as ctx:  # type: Context
        response = await _get_entity(
            entity_id=entity_id,
            include_drives=include_drives,
            include_items=include_items,
            include_folders=include_folders,
            configuration=configuration,
            context=ctx,
        )
        return response


async def _children(folder_id: str, configuration: Configuration, context: Context):
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


@router.get(
    "/folders/{folder_id}/children",
    summary="list drives",
    response_model=ChildrenResponse,
)
async def children(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[ChildrenResponse] = None
    async with Context.start_ep(
        request=request, action="children", response=lambda: response
    ) as ctx:  # type: Context
        response = await _children(
            folder_id=folder_id, configuration=configuration, context=ctx
        )
        return response


async def _list_deleted(drive_id: str, configuration: Configuration, context: Context):
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


@router.get(
    "/drives/{drive_id}/deleted",
    summary="list items of the drive queued for deletion",
    response_model=ChildrenResponse,
)
async def list_deleted(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[ChildrenResponse] = None
    async with Context.start_ep(
        request=request, action="list_deleted", response=lambda: response
    ) as ctx:  # type: Context
        response = await _list_deleted(
            drive_id=drive_id, configuration=configuration, context=ctx
        )
        return response


@router.delete("/items/{item_id}", summary="delete an entity")
async def queue_delete_item(
    request: Request,
    item_id: str,
    erase: bool = False,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, action="queue_delete_item", with_attributes={"itemId": item_id}
    ) as ctx:  # type: Context
        dbs = configuration.doc_dbs
        items_db, _, _, deleted_db = (
            dbs.items_db,
            dbs.folders_db,
            dbs.drives_db,
            dbs.deleted_db,
        )

        doc = await db_get(
            partition_keys={"item_id": item_id}, docdb=items_db, context=ctx
        )

        if not erase:
            deleted_doc = {
                "deleted_id": doc["item_id"],
                "drive_id": doc["drive_id"],
                "type": doc["type"],
                "kind": "item",
                "related_id": doc["related_id"],
                "name": doc["name"],
                "parent_folder_id": doc["folder_id"],
                "group_id": doc["group_id"],
                "metadata": doc["metadata"],
            }
            deleted_db = configuration.doc_dbs.deleted_db
            await db_post(doc=deleted_doc, docdb=deleted_db, context=ctx)

        await db_delete(
            docdb=items_db,
            doc={"item_id": doc["item_id"], "group_id": doc["group_id"]},
            context=ctx,
        )
        return {}


@router.delete("/folders/{folder_id}", summary="delete a folder and its content")
async def queue_delete_folder(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request,
        action="queue_delete_folder",
        with_attributes={"itemId": folder_id},
    ) as ctx:  # type: Context
        dbs = configuration.doc_dbs
        folders_db, _, deleted_db = (
            dbs.folders_db,
            dbs.drives_db,
            dbs.deleted_db,
        )

        doc = await db_get(
            partition_keys={"folder_id": folder_id}, docdb=folders_db, context=ctx
        )

        doc = {
            "deleted_id": doc["folder_id"],
            "drive_id": doc["drive_id"],
            "type": doc["type"],
            "kind": "folder",
            "name": doc["name"],
            "parent_folder_id": doc["parent_folder_id"],
            "related_id": "",
            "group_id": doc["group_id"],
            "metadata": doc["metadata"],
        }

        deleted_db = configuration.doc_dbs.deleted_db

        await db_post(doc=doc, docdb=deleted_db, context=ctx)
        await db_delete(
            docdb=folders_db,
            doc={"folder_id": doc["deleted_id"], "group_id": doc["group_id"]},
            context=ctx,
        )
        return {}


@router.delete("/drives/{drive_id}", summary="delete drive, need to be empty")
async def delete_drive(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, action="delete_drive", with_attributes={"drive_id": drive_id}
    ) as ctx:  # type: Context
        drives_db = configuration.doc_dbs.drives_db
        entities, deleted = await asyncio.gather(
            _children(folder_id=drive_id, configuration=configuration, context=ctx),
            _list_deleted(drive_id=drive_id, configuration=configuration, context=ctx),
        )

        if len(entities.folders + entities.items + deleted.items + deleted.folders) > 0:
            raise HTTPException(
                status_code=428,
                detail="the drive needs to be empty and purged before deletion",
            )

        doc = await db_get(
            partition_keys={"drive_id": drive_id}, docdb=drives_db, context=ctx
        )
        await db_delete(docdb=drives_db, doc=doc, context=ctx)
        return {}


@router.delete(
    "/drives/{drive_id}/purge",
    summary="purge drive's items scheduled for deletion",
    response_model=PurgeResponse,
)
async def purge_drive(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    response: Optional[PurgeResponse] = None
    async with Context.start_ep(
        request=request,
        action="purge_drive",
        response=lambda: response,
        with_attributes={"drive_id": drive_id},
    ) as ctx:  # type: Context
        dbs = configuration.doc_dbs
        folders_db, items_db = dbs.folders_db, dbs.items_db

        deleted = await _list_deleted(
            drive_id=drive_id, configuration=configuration, context=ctx
        )

        deletion_items = [
            db_delete(docdb=items_db, doc=item_to_doc(f), context=ctx)
            for f in deleted.items
        ]
        deletion_folders = [
            db_delete(docdb=folders_db, doc=folder_to_doc(f), context=ctx)
            for f in deleted.folders
        ]

        skip_items = {e.itemId for e in deleted.items}

        children_folder = [
            purge_folder(
                request=request,
                drive_id=drive_id,
                folder_id=f.folderId,
                skip_folders=set(),
                skip_items=skip_items,
                configuration=configuration,
                context=ctx,
            )
            for f in deleted.folders
        ]

        deletion_children_folders = await asyncio.gather(*children_folder)

        deletion_rec_items = list(flatten([d for d, _, _ in deletion_children_folders]))
        deletion_rec_folders = list(
            flatten([d for _, d, _ in deletion_children_folders])
        )
        list_items = list(flatten([d for _, _, d in deletion_children_folders]))
        all_entities_delete = [
            *deletion_rec_items,
            *deletion_rec_folders,
            *deletion_items,
            *deletion_folders,
        ]

        await asyncio.gather(*all_entities_delete)

        deleted_db = configuration.doc_dbs.deleted_db
        deleted_db_items = await db_query(
            docdb=deleted_db, key="drive_id", value=drive_id, max_count=100, context=ctx
        )
        await asyncio.gather(
            *[
                db_delete(docdb=deleted_db, doc=item, context=ctx)
                for item in deleted_db_items
            ]
        )

        response = PurgeResponse(
            foldersCount=len(deletion_folders) + len(deletion_rec_folders),
            itemsCount=len(deletion_items) + len(deletion_rec_items),
            items=list_items + deleted.items,
        )
        return response


async def purge_folder(
    request: Request,
    drive_id: str,
    folder_id: str,
    skip_folders: Set[str],
    skip_items: Set[str],
    configuration: Configuration,
    context: Context,
) -> Tuple[List[Coroutine], List[Coroutine], List[ItemResponse]]:
    async with context.start(action="purge folder") as ctx:
        doc_dbs = configuration.doc_dbs
        content = await _children(
            folder_id=folder_id, configuration=configuration, context=ctx
        )

        delete_items = [
            db_delete(docdb=doc_dbs.items_db, doc=item_to_doc(f), context=ctx)
            for f in content.items
            if f.itemId not in skip_items
        ]
        delete_folders = [
            db_delete(docdb=doc_dbs.folders_db, doc=folder_to_doc(f), context=ctx)
            for f in content.folders
            if f.folderId not in skip_items
        ]

        skip_items = skip_items.union({f.itemId for f in content.items})

        children_folder = [
            purge_folder(
                request=request,
                drive_id=drive_id,
                folder_id=f.folderId,
                context=ctx,
                skip_folders=skip_folders,
                skip_items=skip_items,
                configuration=configuration,
            )
            for f in content.folders
            if f.folderId not in skip_folders
        ]

        deletion_rec_folders = await asyncio.gather(*children_folder)

        return (
            delete_items + list(flatten([d for d, _, _ in deletion_rec_folders])),
            delete_folders + list(flatten([d for _, d, _ in deletion_rec_folders])),
            content.items + list(flatten([d for _, _, d in deletion_rec_folders])),
        )


async def get_items_rec(
    request, folder_id: str, configuration: Configuration, context: Context
):
    resp = await _children(
        folder_id=folder_id, configuration=configuration, context=context
    )

    children_folders = await asyncio.gather(
        *[
            get_items_rec(
                request=request,
                folder_id=folder.folderId,
                configuration=configuration,
                context=context,
            )
            for folder in resp.folders
        ]
    )

    folders = [folder.folderId for folder in resp.folders] + list(
        flatten([list(folders) for items, folders in children_folders])
    )
    items = [item.itemId for item in resp.items] + list(
        flatten([list(items) for items, folders in children_folders])
    )

    return items, folders
