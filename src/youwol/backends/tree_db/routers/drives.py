# standard library
import asyncio
import itertools

# third parties
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

# Youwol backends
from youwol.backends.tree_db.configurations import Configuration, get_configuration

# Youwol utilities
from youwol.utils import private_group_id, user_info
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    DefaultDriveResponse,
    DriveResponse,
    PurgeResponse,
    RenameBody,
)

# relative
from ..utils import (
    db_delete,
    db_get,
    db_post,
    db_query,
    entities_children,
    folder_to_doc,
    get_default_drive,
    get_drive,
    item_to_doc,
    list_deleted,
)
from .folders import purge_folder

router = APIRouter(tags=["treedb-backend.drives"])
flatten = itertools.chain.from_iterable


# drives
@router.post(
    "/drives/{drive_id}",
    summary="Update a drive properties.",
    response_model=DriveResponse,
)
async def update_drive(
    request: Request,
    drive_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
) -> DriveResponse:
    """
    Updates a drive properties.

    Parameters:
        request: Incoming request.
        drive_id: ID of the drive.
        body: Update details.
        configuration: Injected configuration of the service.

    Return:
        Description of the drive.
    """
    async with Context.start_ep(
        request=request,
        action="update_drive",
        body=body,
        with_attributes={"drive_id": drive_id},
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


# drives
@router.get(
    "/default-drive",
    response_model=DefaultDriveResponse,
    summary="get user's default drive",
)
async def get_default_user_drive(
    request: Request, configuration: Configuration = Depends(get_configuration)
) -> DefaultDriveResponse:
    """
    Retrieves properties of the default user's drive.

    Parameters:
        request: Incoming request.
        configuration: Injected configuration of the service.

    Return:
        Description of the drive.
    """
    user = user_info(request)
    return await get_default_drive(
        request=request, group_id=private_group_id(user), configuration=configuration
    )


# drives
@router.get(
    "/drives/{drive_id}",
    summary="Retrieves a drive properties.",
    response_model=DriveResponse,
)
async def get_drive_details(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> DriveResponse:
    """
    Retrieves a drive properties.

    Parameters:
        request: Incoming request.
        drive_id: ID of the drive.
        configuration: Injected configuration of the service.

    Return:
        Description of the drive.
    """

    async with Context.start_ep(
        request=request,
        action="get_drive",
        with_attributes={"drive_id": drive_id},
    ) as ctx:  # type: Context
        response = await get_drive(
            drive_id=drive_id, configuration=configuration, context=ctx
        )
        return response


# drives
@router.delete(
    "/drives/{drive_id}", summary="Delete a drive, the drive needs to be empty."
)
async def delete_drive(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Delete a drive, the drive needs to be empty.

    Parameters:
        request: Incoming request
        drive_id: Drive's ID.
        configuration: Injected configuration of the service.

    Return:
        Empty JSON response.
    """

    async with Context.start_ep(
        request=request, action="delete_drive", with_attributes={"drive_id": drive_id}
    ) as ctx:  # type: Context
        drives_db = configuration.doc_dbs.drives_db
        entities, deleted = await asyncio.gather(
            entities_children(
                folder_id=drive_id, configuration=configuration, context=ctx
            ),
            list_deleted(drive_id=drive_id, configuration=configuration, context=ctx),
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


# drives
@router.delete(
    "/drives/{drive_id}/purge",
    summary="Purge drive's entities scheduled for deletion.",
    response_model=PurgeResponse,
)
async def purge_drive(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> PurgeResponse:
    """
    Purge drive's entities scheduled for deletion.

    Parameters:
        request: Incoming request
        drive_id: Drive's ID.
        configuration: Injected configuration of the service.

    Return:
        Purge description.
    """
    async with Context.start_ep(
        request=request,
        action="purge_drive",
        with_attributes={"drive_id": drive_id},
    ) as ctx:  # type: Context
        dbs = configuration.doc_dbs
        folders_db, items_db = dbs.folders_db, dbs.items_db

        deleted = await list_deleted(
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
