# standard library
import asyncio
import itertools
import uuid

from collections.abc import Coroutine

# third parties
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

# Youwol backends
from youwol.backends.tree_db.configurations import (
    Configuration,
    Constants,
    get_configuration,
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
    ChildrenResponse,
    DefaultDriveResponse,
    DriveBody,
    DriveResponse,
    DrivesResponse,
    FolderBody,
    FolderResponse,
    Group,
    GroupsResponse,
    ItemResponse,
    PathResponse,
    PurgeResponse,
    RenameBody,
)

# relative
from .routers import router_entities, router_items
from .utils import (
    db_delete,
    db_get,
    db_post,
    db_query,
    doc_to_drive_response,
    doc_to_folder,
    entities_children,
    folder_to_doc,
    get_drive,
    get_folder,
    get_folders_rec,
    get_parent,
    item_to_doc,
    list_deleted,
)

router = APIRouter(tags=["treedb-backend"])
router.include_router(router_entities)
router.include_router(router_items)
flatten = itertools.chain.from_iterable


@router.get(
    "/groups", response_model=GroupsResponse, summary="List user's subscribed groups."
)
async def get_groups(request: Request) -> GroupsResponse:
    """
    Lists user's subscribed groups.

    Parameters:
        request: Incoming request.

    Return:
        User's groups.
    """
    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    return GroupsResponse(
        groups=(
            [Group(id=private_group_id(user), path="private")]
            + [Group(id=str(to_group_id(g)), path=g) for g in groups if g]
        )
    )


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
    "/groups/{group_id}/drives",
    summary="Create a new drive.",
    response_model=DriveResponse,
)
async def create_drive(
    request: Request,
    group_id: str,
    drive: DriveBody,
    configuration: Configuration = Depends(get_configuration),
) -> DriveResponse:
    """
    Creates a new drive.

    Parameters:
        request: Incoming request.
        group_id: Group in which the drive belongs.
        drive: Description of the drive.
        configuration: Injected configuration of the service.

    Return:
        Drive attributes.
    """

    async with Context.start_ep(
        request=request, action="create drive", body=drive
    ) as ctx:  # type: Context
        response = await _create_drive(
            group_id=group_id, drive=drive, configuration=configuration, context=ctx
        )
        return response


@router.get(
    "/groups/{group_id}/drives",
    summary="List the available drives under a particular group.",
    response_model=DrivesResponse,
)
async def list_drives(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> DrivesResponse:
    """
    Lists the available drives under a particular group.

    Parameters:
        request: Incoming request.
        group_id: Group in which the drives belong.
        configuration: Injected configuration of the service.

    Return:
        The list of available drives.
    """
    async with Context.start_ep(
        request=request,
        action="list_drives",
        with_attributes={"groupId": group_id},
    ) as ctx:  # type: Context
        ensure_group_permission(request=request, group_id=group_id)

        docdb_drive = configuration.doc_dbs.drives_db
        drives = await docdb_drive.query(
            query_body=f"group_id={group_id}#100",
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )
        response = DrivesResponse(
            drives=[doc_to_drive_response(d) for d in drives["documents"]]
        )
        return response


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
    return await _get_default_drive(
        request=request, group_id=private_group_id(user), configuration=configuration
    )


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
            return await _create_folder(
                parent_folder_id=parent_folder_id,
                folder=FolderBody(name=name, folderId=folder_id),
                configuration=configuration,
                context=ctx,
            )


async def _get_default_drive(
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
            await _create_drive(
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


@router.get(
    "/groups/{group_id}/default-drive",
    response_model=DefaultDriveResponse,
    summary="Retrieves the default drive of a group.",
)
async def get_default_drive(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> DefaultDriveResponse:
    """
    Retrieves properties of the default drive of a group.

    Parameters:
        request: Incoming request.
        group_id: ID of the parent group.
        configuration: Injected configuration of the service.

    Return:
        Description of the drive.
    """
    return await _get_default_drive(request, group_id, configuration)


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
