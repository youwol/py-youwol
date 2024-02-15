# standard library
import asyncio
import itertools

# third parties
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from starlette.requests import Request

# Youwol utilities
from youwol.utils import AnyDict
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    EntityResponse,
    FolderResponse,
    MoveItemBody,
    MoveResponse,
)

# relative
from ..configurations import Configuration, get_configuration
from ..utils import (
    db_post,
    db_query,
    doc_to_drive_response,
    doc_to_folder,
    doc_to_item,
    entities_children,
)

router = APIRouter(tags=["treedb-backend.entities"])
flatten = itertools.chain.from_iterable


@router.post(
    "/move",
    response_model=MoveResponse,
    summary="Move an entity, folder or item, from on location to another one.",
)
async def move(
    request: Request,
    body: MoveItemBody,
    configuration: Configuration = Depends(get_configuration),
) -> MoveResponse:
    """
    Move an entity, folder or item, from on location to another one.

    Parameters:
        request: Incoming request.
        body: Move specification
        configuration: Injected configuration of the service.

    Return:
        Description of the executed task result.
    """
    async with Context.start_ep(request=request, action="move", body=body) as ctx:
        items_db = configuration.doc_dbs.items_db
        folders_db = configuration.doc_dbs.folders_db
        items: list[AnyDict]
        folders: list[AnyDict]
        to_folder_or_drive: EntityResponse
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
            to_move = await entities_children(
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
    summary="Retrieves an entity (drive, folder, or item) from its ID.",
)
async def get_entity(
    request: Request,
    entity_id: str,
    include_drives: bool = QueryParam(True, alias="include-drives"),
    include_folders: bool = QueryParam(True, alias="include-folders"),
    include_items: bool = QueryParam(True, alias="include-items"),
    configuration: Configuration = Depends(get_configuration),
) -> EntityResponse:
    """
    Retrieves an entity (drive, folder, or item) from its ID.

    Parameters:
        request: Incoming request.
        entity_id: Entity's ID.
        include_drives: Whether to look up in drives.
        include_folders: Whether to look up in folders.
        include_items: Whether to look up in items.
        configuration: Injected configuration of the service.

    Return:
        Description of the entity.
    """
    async with Context.start_ep(
        request=request, action="get_entity"
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
