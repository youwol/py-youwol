# standard library
import asyncio

# third parties
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request

# Youwol backends
from youwol.backends.assets_gateway.configurations import (
    Configuration,
    get_configuration,
)

# Youwol utilities
from youwol.utils import ensure_group_permission
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
    HealthzResponse,
    ItemBody,
    ItemResponse,
    ItemsResponse,
    MoveItemBody,
    MoveResponse,
    PathResponse,
    PurgeResponse,
    RenameBody,
)

# relative
from .files_backend import remove_file_impl
from .flux_backend import delete_project_impl
from .stories_backend import delete_story_impl

router = APIRouter(tags=["assets-gateway.flux-backend"])


@router.get(
    "/healthz", summary="return status of the service", response_model=HealthzResponse
)
async def healthz(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.healthz(
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys)
        )


@router.put(
    "/groups/{group_id}/drives", summary="create a drive", response_model=DriveResponse
)
async def create_drive(
    request: Request,
    group_id: str,
    drive: DriveBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        ensure_group_permission(request=request, group_id=group_id)
        return await configuration.treedb_client.create_drive(
            group_id=group_id,
            body=drive.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/groups/{group_id}/drives", summary="list drives", response_model=DrivesResponse
)
async def list_drives(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_drives(
            group_id=group_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post(
    "/drives/{drive_id}", summary="update a drive", response_model=DriveResponse
)
async def update_drive(
    request: Request,
    drive_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        drive = await configuration.treedb_client.get_drive(
            drive_id=drive_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=drive["groupId"])
        return await configuration.treedb_client.update_drive(
            drive_id=drive_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get("/drives/{drive_id}", summary="get a drive", response_model=DriveResponse)
async def get_drive(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_drive(
            drive_id=drive_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
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
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_default_drive(
            group_id=group_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/default-drive",
    response_model=DefaultDriveResponse,
    summary="get user's default drive",
)
async def get_default_user_drive(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_default_user_drive(
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys)
        )


@router.put(
    "/folders/{parent_folder_id}",
    summary="create a folder",
    response_model=FolderResponse,
)
async def create_folder(
    request: Request,
    parent_folder_id: str,
    body: FolderBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        folder = await configuration.treedb_client.get_folder(
            folder_id=parent_folder_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=folder["groupId"])

        return await configuration.treedb_client.create_folder(
            parent_folder_id=parent_folder_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post(
    "/folders/{folder_id}", summary="update a folder", response_model=FolderResponse
)
async def update_folder(
    request: Request,
    folder_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        folder = await configuration.treedb_client.get_folder(
            folder_id=folder_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=folder["groupId"])

        return await configuration.treedb_client.update_folder(
            folder_id=folder_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/folders/{folder_id}", summary="get a folder", response_model=FolderResponse
)
async def get_folder(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_folder(
            folder_id=folder_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.put(
    "/folders/{folder_id}/items", summary="create an item", response_model=ItemResponse
)
async def create_item(
    request: Request,
    folder_id: str,
    item: ItemBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        folder = await configuration.treedb_client.get_folder(
            folder_id=folder_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=folder["groupId"])

        return await configuration.treedb_client.create_item(
            folder_id=folder_id,
            body=item.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post("/items/{item_id}", summary="update an item", response_model=ItemResponse)
async def update_item(
    request: Request,
    item_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        item = await configuration.treedb_client.get_item(
            item_id=item_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=item["groupId"])

        assets_client = configuration.assets_client
        try:
            asset = await assets_client.get_asset(
                asset_id=item_id, headers=ctx.headers()
            )
            await assets_client.update_asset(
                asset_id=asset["assetId"],
                body={"name": body.name},
                headers=ctx.headers(),
            )

        except HTTPException as e:
            if e.status_code != 404:
                raise e

        return await configuration.treedb_client.update_item(
            item_id=item_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get("/items/{item_id}", summary="get an item", response_model=ItemResponse)
async def get_item(
    request: Request,
    item_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_item(
            item_id=item_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.get(
    "/items/from-asset/{asset_id}",
    summary="get an item from asset's id",
    response_model=ItemsResponse,
)
async def get_items_by_related_id(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_items_from_asset(
            asset_id=asset_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


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
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_path(
            item_id=item_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


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
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_path_folder(
            folder_id=folder_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.post("/move", response_model=MoveResponse, summary="move an item")
async def move(
    request: Request,
    body: MoveItemBody,
    configuration: Configuration = Depends(get_configuration),
):
    asset_client = configuration.assets_client
    async with Context.start_ep(request=request) as ctx:
        treedb_client = configuration.treedb_client
        entity, folder = await asyncio.gather(
            treedb_client.get_entity(entity_id=body.targetId, headers=ctx.headers()),
            treedb_client.get_folder(
                folder_id=body.destinationFolderId, headers=ctx.headers()
            ),
        )
        from_group_id = entity["entity"]["groupId"]
        to_group_id = folder["groupId"]
        ensure_group_permission(request=request, group_id=from_group_id)
        ensure_group_permission(request=request, group_id=to_group_id)
        headers = ctx.headers(lambda header_keys: header_keys)
        moved_items = await configuration.treedb_client.move(
            body=body.dict(),
            headers=headers,
        )
        if from_group_id != to_group_id:
            # In this path (change in owning group), we synchronize the owning group of the related assets
            for item in moved_items["items"]:
                asset = await asset_client.get_asset(
                    asset_id=item["assetId"], headers=headers
                )
                await asset_client.update_asset(
                    asset_id=asset["assetId"],
                    body={"groupId": item["groupId"]},
                    headers=headers,
                )
        return moved_items


@router.post(
    "/items/{item_id}/borrow", response_model=ItemResponse, summary="borrow item"
)
async def borrow(
    request: Request,
    item_id: str,
    body: BorrowBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        tree_db, assets_db = configuration.treedb_client, configuration.assets_client

        parent = await tree_db.get_entity(
            entity_id=body.destinationFolderId, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=parent["entity"]["groupId"])

        tree_item, destination = await asyncio.gather(
            tree_db.get_item(item_id=item_id, headers=ctx.headers()),
            tree_db.get_entity(
                entity_id=body.destinationFolderId, headers=ctx.headers()
            ),
        )
        await ctx.info(
            text="[tree_item, destination] retrieved",
            data={"tree_item": tree_item, "destination": destination},
        )
        asset, user_permission, access_policy = await asyncio.gather(
            assets_db.get_asset(asset_id=tree_item["assetId"], headers=ctx.headers()),
            assets_db.get_permissions(
                asset_id=tree_item["assetId"], headers=ctx.headers()
            ),
            assets_db.get_access_policy(
                asset_id=tree_item["assetId"],
                group_id=destination["entity"]["groupId"],
                headers=ctx.headers(),
                params={"include-inherited": "false"},
            ),
            return_exceptions=True,
        )
        await ctx.info(
            text="[asset, user_permission, access_policy] retrieved",
            data={
                "asset": asset,
                "user_permission": user_permission,
                "access_policy": access_policy
                if not isinstance(access_policy, BaseException)
                else "No policy found",
            },
        )
        if not user_permission["share"]:
            raise HTTPException(
                status_code=403, detail="The resource can not be shared"
            )

        resp = await configuration.treedb_client.borrow(
            item_id=item_id,
            body=body.dict(),
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )
        if (
            not isinstance(access_policy, BaseException)
            and access_policy["read"] == "owning"
        ):
            await ctx.info(text="Borrowing in owning group => RAS")

        if not isinstance(access_policy, BaseException):
            await ctx.info(
                text="Borrowing in group already included in access policy=> RAS"
            )

        if (
            isinstance(access_policy, HTTPException)
            and access_policy.status_code == 404
        ):
            await assets_db.put_access_policy(
                asset_id=tree_item["assetId"],
                group_id=destination["entity"]["groupId"],
                body={"read": "authorized", "share": "authorized"},
                headers=ctx.headers(),
            )
        return resp


@router.get(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    summary="get an entity from id in [item, folder, drive]",
)
async def get_entity(
    request: Request,
    entity_id: str,
    include_drives: bool = Query(True, alias="include-drives"),
    include_folders: bool = Query(True, alias="include-folders"),
    include_items: bool = Query(True, alias="include-items"),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_entity(
            entity_id=entity_id,
            include_drives=include_drives,
            include_folders=include_folders,
            include_items=include_items,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
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
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_children(
            folder_id=folder_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


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
    async with Context.start_ep(request=request) as ctx:
        return await configuration.treedb_client.get_deleted(
            drive_id=drive_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/items/{item_id}", summary="delete an entity")
async def queue_delete_item(
    request: Request,
    item_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        item = await configuration.treedb_client.get_item(
            item_id=item_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=item["groupId"])

        return await configuration.treedb_client.remove_item(
            item_id=item_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/folders/{folder_id}", summary="delete a folder and its content")
async def queue_delete_folder(
    request: Request,
    folder_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        folder = await configuration.treedb_client.get_folder(
            folder_id=folder_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=folder["groupId"])

        return await configuration.treedb_client.remove_folder(
            folder_id=folder_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


@router.delete("/drives/{drive_id}", summary="delete drive, need to be empty")
async def delete_drive(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        drive = await configuration.treedb_client.get_drive(
            drive_id=drive_id, headers=ctx.headers()
        )
        ensure_group_permission(request=request, group_id=drive["groupId"])

        return await configuration.treedb_client.delete_drive(
            drive_id=drive_id,
            headers=ctx.headers(from_req_fwd=lambda header_keys: header_keys),
        )


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
    async def erase_flux_project(raw_id: str, context: Context):
        await delete_project_impl(
            project_id=raw_id, purge=False, configuration=configuration, context=context
        )

    async def erase_story(raw_id: str, context: Context):
        await delete_story_impl(
            story_id=raw_id, purge=False, configuration=configuration, context=context
        )

    async def erase_file(raw_id: str, context: Context):
        await remove_file_impl(
            file_id=raw_id, purge=False, configuration=configuration, context=context
        )

    factory = {
        "flux-project": erase_flux_project,
        "story": erase_story,
        "data": erase_file,
    }
    assets_db = configuration.assets_client

    async with Context.start_ep(request=request) as ctx:
        tree_db = configuration.treedb_client
        drive = await tree_db.get_drive(drive_id=drive_id, headers=ctx.headers())
        ensure_group_permission(request=request, group_id=drive["groupId"])

        resp = await tree_db.purge_drive(drive_id=drive_id, headers=ctx.headers())
        errors_raw_deletion = []
        errors_asset_deletion = []
        original_items = [item for item in resp["items"] if not item["borrowed"]]
        await ctx.info(text=f"Found {len(original_items)} to purge")
        for to_delete in original_items:
            await ctx.info(text="Delete item", data=to_delete)

            if to_delete["kind"] not in factory:
                await ctx.info(
                    text="Delete asset un-affiliated to backend", data=to_delete
                )
                try:
                    await assets_db.delete_asset(
                        asset_id=to_delete["assetId"], headers=ctx.headers()
                    )
                except HTTPException:
                    await ctx.warning("Error while deleting asset", data=to_delete)
                    errors_asset_deletion.append(to_delete["assetId"])
                continue

            # order do matters here:
            # first raw part deletion
            erase_raw_part = factory[to_delete["kind"]]
            try:
                await erase_raw_part(raw_id=to_delete["rawId"], context=ctx)
            except HTTPException:
                await ctx.warning(
                    "Error while deleting raw part of asset", data=to_delete
                )
                errors_raw_deletion.append(to_delete["rawId"])

            # then asset deletion
            try:
                await assets_db.delete_asset(
                    asset_id=to_delete["assetId"], headers=ctx.headers()
                )
            except HTTPException:
                await ctx.warning("Error while deleting asset", data=to_delete)
                errors_asset_deletion.append(to_delete["assetId"])

        for to_delete in [item for item in resp["items"] if item["borrowed"]]:
            related_items = await tree_db.get_items_from_asset(
                asset_id=to_delete["assetId"], headers=ctx.headers()
            )
            borrowed_items_in_group = [
                item
                for item in related_items["items"]
                if item["borrowed"] and item["groupId"] == to_delete["groupId"]
            ]
            if len(borrowed_items_in_group) == 0:
                await ctx.info(
                    text="Remove access policy for (asset, group)",
                    data={"toDelete": to_delete},
                )
                await assets_db.delete_access_policy(
                    asset_id=to_delete["assetId"],
                    group_id=to_delete["groupId"],
                    headers=ctx.headers(),
                )

        if errors_raw_deletion or errors_asset_deletion:
            raise HTTPException(
                status_code=500,
                detail={
                    "treedbResp": resp,
                    "errorsRawDeletion": errors_raw_deletion,
                    "errorsAssetDeletion": errors_asset_deletion,
                },
            )
        return PurgeResponse(**resp)
