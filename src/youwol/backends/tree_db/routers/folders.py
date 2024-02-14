# standard library
import asyncio
import itertools

from collections.abc import Coroutine

# third parties
from fastapi import APIRouter, Depends
from starlette.requests import Request

# Youwol backends
from youwol.backends.tree_db.configurations import Configuration, get_configuration

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    ChildrenResponse,
    FolderBody,
    FolderResponse,
    ItemResponse,
    PathResponse,
    RenameBody,
)

# relative
from ..utils import (
    create_folder,
    db_delete,
    db_get,
    db_post,
    doc_to_folder,
    entities_children,
    folder_to_doc,
    get_folder,
    get_folders_rec,
    item_to_doc,
)

router = APIRouter(tags=["treedb-backend.folders"])
flatten = itertools.chain.from_iterable


@router.put(
    "/folders/{parent_folder_id}",
    summary="create a folder",
    response_model=FolderResponse,
)
async def create_child_folder(
    request: Request,
    parent_folder_id: str,
    folder: FolderBody,
    configuration: Configuration = Depends(get_configuration),
) -> FolderResponse:
    """
    Creates a new folder.

    Parameters:
        request: Incoming request.
        parent_folder_id: ID of the parent folder.
        folder: folder properties.
        configuration: Injected configuration of the service.

    Return:
        Description of the folder.
    """
    async with Context.start_ep(
        request=request,
        action="create_folder",
        body=folder,
        with_attributes={"parent_folder_id": parent_folder_id},
    ) as ctx:  # type: Context
        response = await create_folder(
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
) -> FolderResponse:
    """
    Updates a folder properties.

    Parameters:
        request: Incoming request.
        folder_id: ID of the folder.
        body: Update details.
        configuration: Injected configuration of the service.

    Return:
        Description of the drive.
    """
    async with Context.start_ep(
        request=request,
        action="update_folder",
        body=body,
        with_attributes={"folder_id": folder_id},
    ) as ctx:  # type: Context
        folders_db = configuration.doc_dbs.folders_db
        doc = await db_get(
            partition_keys={"folder_id": folder_id}, docdb=folders_db, context=ctx
        )
        doc = {**doc, **{"name": body.name}}
        await db_post(docdb=folders_db, doc=doc, context=ctx)

        response = doc_to_folder(doc)
        return response


@router.get(
    "/folders/{folder_id}",
    summary="Retrieves properties of a folder.",
    response_model=FolderResponse,
)
async def get_folder_details(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> FolderResponse:
    """
    Retrieves properties of a folder.

    Parameters:
        request: Incoming request.
        folder_id: ID of the folder.
        configuration: Injected configuration of the service.

    Return:
        Description of the folder.
    """
    async with Context.start_ep(
        request=request,
        action="get_folder",
        with_attributes={"folder_id": folder_id},
    ) as ctx:  # type: Context
        response = await get_folder(
            folder_id=folder_id, configuration=configuration, context=ctx
        )
        return response


@router.get(
    "/folders/{folder_id}/path",
    summary="Retrieves the full path of a folder.",
    response_model=PathResponse,
)
async def get_path_folder(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> PathResponse:
    """
    Retrieves the full path of a folder.

    Parameters:
        request: Incoming request.
        folder_id: ID of the folder.
        configuration: Injected configuration of the service.

    Return:
        Description of the path.
    """
    async with Context.start_ep(
        request=request,
        action="get_path_folder",
        with_attributes={"folder_id": folder_id},
    ) as ctx:  # type: Context
        folder = await get_folder(
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


@router.get(
    "/folders/{folder_id}/children",
    summary="Query the children of a folder or drive.",
    response_model=ChildrenResponse,
)
async def children(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> ChildrenResponse:
    """
    Query the children of a folder or drive.

    Parameters:
        request: Incoming request
        folder_id: parent folder's ID (or parent's drive ID to request a drive's children).
        configuration: Injected configuration of the service.

    Return:
        Description of the children.
    """
    async with Context.start_ep(
        request=request, action="children"
    ) as ctx:  # type: Context
        response = await entities_children(
            folder_id=folder_id, configuration=configuration, context=ctx
        )
        return response


@router.delete("/folders/{folder_id}", summary="delete a folder and its content")
async def queue_delete_folder(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Queues a folder for deletion (moves into the 'trash').

    Parameters:
        request: Incoming request
        folder_id: Folder's ID.
        configuration: Injected configuration of the service.

    Return:
        Empty JSON response.
    """
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


async def purge_folder(
    request: Request,
    drive_id: str,
    folder_id: str,
    skip_folders: set[str],
    skip_items: set[str],
    configuration: Configuration,
    context: Context,
) -> tuple[list[Coroutine], list[Coroutine], list[ItemResponse]]:
    async with context.start(action="purge folder") as ctx:
        doc_dbs = configuration.doc_dbs
        content = await entities_children(
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
