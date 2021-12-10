import asyncio
import json
from typing import List, Callable, Awaitable, TypeVar
from fastapi import HTTPException


from configuration.clients import RemoteClients, LocalClients
from context import Context
from services.backs.treedb.models import PathResponse, ItemResponse, ItemsResponse, DriveResponse
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.treedb.treedb import TreeDbClient


async def get_remote_paths(
        remote_treedb: TreeDbClient,
        tree_items: ItemsResponse
        ):
    items_path_ = await asyncio.gather(*[
        remote_treedb.get_path(item.itemId)
        for item in tree_items.items
        ])
    items_path = [PathResponse(**p) for p in items_path_]

    def is_borrowed(item: ItemResponse):
        return json.loads(item.metadata)['borrowed']

    owning_location = next((path for path in items_path if not is_borrowed(path.item)), None)
    borrowed_locations = [path for path in items_path if is_borrowed(path.item)]
    return owning_location, borrowed_locations


async def ensure_local_path(path_item: PathResponse, local_treedb: TreeDbClient):

    folders = path_item.folders
    try:
        if folders:
            await local_treedb.get_folder(folder_id=folders[-1].folderId)
        else:
            await local_treedb.get_drive(drive_id=path_item.drive.driveId)
    except HTTPException as e:
        if e.status_code == 404:
            if len(folders) <= 1:
                await ensure_drive(path_item.drive, local_treedb)
            else:
                await ensure_local_path(PathResponse(drive=path_item.drive, folders=folders[0:-1], item=path_item.item),
                                        local_treedb)
            if not folders:
                return
            folder = folders[-1]
            body = {"folderId":  folder.folderId, "name": folder.name}
            await local_treedb.create_folder(parent_folder_id=folder.parentFolderId, body=body)


async def ensure_drive(drive: DriveResponse,  local_treedb: TreeDbClient):

    try:
        await local_treedb.get_drive(drive_id=drive.driveId)
    except HTTPException as e:
        if e.status_code == 404:
            body = {"driveId": drive.driveId, "name": drive.name}
            await local_treedb.create_drive(group_id=drive.groupId, body=body)
            return
        raise e


async def get_local_owning_folder_id(
        owning_location: PathResponse,
        local_treedb: TreeDbClient,
        default_folder_id: str
        ):
    if owning_location:
        await ensure_local_path(owning_location, local_treedb)

    return owning_location.folders[-1].folderId\
        if owning_location\
        else default_folder_id


async def sync_borrowed_items(
        asset_id: str,
        borrowed_locations: List[PathResponse],
        local_treedb: TreeDbClient,
        local_gtw: AssetsGatewayClient
        ):
    await asyncio.gather(*[ensure_local_path(p, local_treedb) for p in borrowed_locations])

    await asyncio.gather(*[
        local_gtw.borrow_tree_item(
            asset_id,
            {'itemId': p.item.itemId, 'destinationFolderId': p.folders[-1].folderId}
            )
        for p in borrowed_locations
        ])

T = TypeVar('T')


async def create_asset_local(
        asset_id: str,
        kind: str,
        default_owning_folder_id,
        get_raw_data: Callable[[], Awaitable[T]],
        to_post_raw_data: Callable[[T], any],
        context: Context
        ):

    local_treedb: TreeDbClient = LocalClients.get_treedb_client(context)
    local_gtw: AssetsGatewayClient = LocalClients.get_assets_gateway_client(context)
    remote_gtw = await RemoteClients.get_assets_gateway_client(context)
    remote_treedb = await RemoteClients.get_treedb_client(context)

    raw_data, metadata, tree_items = await asyncio.gather(
        get_raw_data(),
        remote_gtw.get_asset_metadata(asset_id=asset_id),
        remote_treedb.get_items_from_related_id(related_id=asset_id)
        )

    owning_location, borrowed_locations = await get_remote_paths(
        remote_treedb=remote_treedb,
        tree_items=ItemsResponse(**tree_items)
        )

    owning_folder_id = await get_local_owning_folder_id(
        owning_location=owning_location,
        local_treedb=local_treedb,
        default_folder_id=default_owning_folder_id
        )
    await local_gtw.put_asset_with_raw(
        kind=kind,
        folder_id=owning_folder_id,
        data=to_post_raw_data(raw_data)
        )
    await sync_borrowed_items(
        asset_id=asset_id,
        borrowed_locations=borrowed_locations,
        local_treedb=local_treedb,
        local_gtw=local_gtw
        )
    # the next line is not fetching images
    await local_gtw.update_asset(asset_id=asset_id, body=metadata)
