# standard library
import asyncio
import itertools
import uuid

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
    DefaultDriveResponse,
    DriveBody,
    DriveResponse,
    DrivesResponse,
    FolderBody,
    Group,
    GroupsResponse,
    PurgeResponse,
    RenameBody,
)

# relative
from .routers import router_entities, router_folders, router_items
from .routers.folders import purge_folder
from .utils import (
    create_folder,
    db_delete,
    db_get,
    db_post,
    db_query,
    doc_to_drive_response,
    entities_children,
    folder_to_doc,
    get_drive,
    get_folder,
    item_to_doc,
    list_deleted,
)

router = APIRouter(tags=["treedb-backend"])
router.include_router(router_entities)
router.include_router(router_items)
router.include_router(router_folders)
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
            return await create_folder(
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
