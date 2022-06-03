from fastapi import APIRouter, Depends, Query, HTTPException
from starlette.requests import Request

from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.context import Context
from youwol_utils.http_clients.tree_db_backend import PurgeResponse, ChildrenResponse, EntityResponse, MoveResponse, \
    MoveItemBody, PathResponse, ItemResponse, RenameBody, ItemBody, FolderResponse, DriveResponse, DrivesResponse, \
    DriveBody, FolderBody, ItemsResponse, HealthzResponse, BorrowBody, DefaultDriveResponse

router = APIRouter(tags=["assets-gateway.flux-backend"])


@router.get("/healthz",
            summary="return status of the service",
            response_model=HealthzResponse)
async def healthz(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.healthz(
            headers=ctx.headers()
        )


@router.put("/groups/{group_id}/drives",
            summary="create a drive",
            response_model=DriveResponse)
async def create_drive(
        request: Request,
        group_id: str,
        drive: DriveBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.create_drive(
            group_id=group_id,
            body=drive.dict(),
            headers=ctx.headers()
        )


@router.get("/groups/{group_id}/drives",
            summary="list drives",
            response_model=DrivesResponse)
async def list_drives(
        request: Request,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_drives(
            group_id=group_id,
            headers=ctx.headers()
        )


@router.post("/drives/{drive_id}",
             summary="update a drive",
             response_model=DriveResponse)
async def update_drive(
        request: Request,
        drive_id: str,
        body: RenameBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.update_drive(
            drive_id=drive_id,
            body=body.dict(),
            headers=ctx.headers()
        )


@router.get("/drives/{drive_id}",
            summary="get a drive",
            response_model=DriveResponse)
async def get_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_drive(
            drive_id=drive_id,
            headers=ctx.headers()
        )


@router.get("/groups/{group_id}/default-drive",
            response_model=DefaultDriveResponse, summary="get group's default drive")
async def get_default_drive(
        request: Request,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_default_drive(
            group_id=group_id,
            headers=ctx.headers()
        )


@router.get("/default-drive",
            response_model=DefaultDriveResponse, summary="get user's default drive")
async def get_default_user_drive(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_default_user_drive(headers=ctx.headers())


@router.put("/folders/{parent_folder_id}",
            summary="create a folder",
            response_model=FolderResponse)
async def create_folder(
        request: Request,
        parent_folder_id: str,
        folder: FolderBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.create_folder(
            parent_folder_id=parent_folder_id,
            body=folder.dict(),
            headers=ctx.headers()
        )


@router.post("/folders/{folder_id}",
             summary="update a folder",
             response_model=FolderResponse)
async def update_folder(
        request: Request,
        folder_id: str,
        body: RenameBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.update_folder(
            folder_id=folder_id,
            body=body.dict(),
            headers=ctx.headers()
        )


@router.get("/folders/{folder_id}",
            summary="get a folder",
            response_model=FolderResponse)
async def get_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_folder(
            folder_id=folder_id,
            headers=ctx.headers()
        )


@router.put("/folders/{folder_id}/items",
            summary="create an item",
            response_model=ItemResponse)
async def create_item(
        request: Request,
        folder_id: str,
        item: ItemBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.create_item(
            folder_id=folder_id,
            body=item.dict(),
            headers=ctx.headers()
        )


@router.post("/items/{item_id}",
             summary="update an item",
             response_model=ItemResponse)
async def update_item(
        request: Request,
        item_id: str,
        body: RenameBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        assets_client = configuration.assets_client
        try:
            asset = await assets_client.get_asset(asset_id=item_id, headers=ctx.headers())
            await assets_client.update_asset(asset_id=asset['assetId'], body={"name": body.name},
                                             headers=ctx.headers())

        except HTTPException as e:
            if e.status_code != 404:
                raise e

        return await configuration.treedb_client.update_item(
            item_id=item_id,
            body=body.dict(),
            headers=ctx.headers()
        )


@router.get("/items/{item_id}",
            summary="get an item",
            response_model=ItemResponse)
async def get_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_item(
            item_id=item_id,
            headers=ctx.headers()
        )


@router.get("/items/from-asset/{asset_id}",
            summary="get an item from asset's id",
            response_model=ItemsResponse)
async def get_items_by_related_id(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_items_from_asset(
            asset_id=asset_id,
            headers=ctx.headers()
        )


@router.get("/items/{item_id}/path",
            summary="get the path of an item",
            response_model=PathResponse)
async def get_path(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_path(
            item_id=item_id,
            headers=ctx.headers()
        )


@router.get("/folders/{folder_id}/path",
            summary="get the path of a folder",
            response_model=PathResponse)
async def get_path_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_path_folder(
            folder_id=folder_id,
            headers=ctx.headers()
        )


@router.post("/move",
             response_model=MoveResponse,
             summary="move an item")
async def move(
        request: Request,
        body: MoveItemBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.move(
            body=body.dict(),
            headers=ctx.headers()
        )


@router.post("/items/{item_id}/borrow",
             response_model=ItemResponse,
             summary="borrow item")
async def borrow(
        request: Request,
        item_id: str,
        body: BorrowBody,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        tree_db, assets_db = configuration.treedb_client, configuration.assets_client
        tree_item = await tree_db.get_item(item_id=item_id, headers=ctx.headers())
        permission = await assets_db.get_permissions(asset_id=tree_item['assetId'], headers=ctx.headers())
        if not permission['share']:
            raise HTTPException(status_code=403, detail='The resource can not be shared')

        return await configuration.treedb_client.borrow(
            item_id=item_id,
            body=body.dict(),
            headers=ctx.headers()
        )


@router.get("/entities/{entity_id}",
            response_model=EntityResponse,
            summary="get an entity from id in [item, folder, drive]"
            )
async def get_entity(
        request: Request,
        entity_id: str,
        include_drives: bool = Query(True, alias="include-drives"),
        include_folders: bool = Query(True, alias="include-folders"),
        include_items: bool = Query(True, alias="include-items"),
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_entity(
            entity_id=entity_id,
            include_drives=include_drives,
            include_folders=include_folders,
            include_items=include_items,
            headers=ctx.headers()
        )


@router.get("/folders/{folder_id}/children",
            summary="list drives",
            response_model=ChildrenResponse)
async def children(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_children(
            folder_id=folder_id,
            headers=ctx.headers()
        )


@router.get("/drives/{drive_id}/deleted",
            summary="list items of the drive queued for deletion",
            response_model=ChildrenResponse)
async def list_deleted(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.get_deleted(
            drive_id=drive_id,
            headers=ctx.headers()
        )


@router.delete("/items/{item_id}",
               summary="delete an entity")
async def queue_delete_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.remove_item(
            item_id=item_id,
            headers=ctx.headers()
        )


@router.delete("/folders/{folder_id}",
               summary="delete a folder and its content")
async def queue_delete_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.remove_folder(
            folder_id=folder_id,
            headers=ctx.headers()
        )


@router.delete("/drives/{drive_id}",
               summary="delete drive, need to be empty")
async def delete_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.delete_drive(
            drive_id=drive_id,
            headers=ctx.headers()
        )


@router.delete("/drives/{drive_id}/purge",
               summary="purge drive's items scheduled for deletion",
               response_model=PurgeResponse)
async def purge_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.treedb_client.purge_drive(
            drive_id=drive_id,
            headers=ctx.headers()
        )
