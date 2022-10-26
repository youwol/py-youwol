import asyncio
import json
from typing import List, Callable, Awaitable, TypeVar, cast, Dict, Optional

from fastapi import HTTPException

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import Context
from youwol_utils.http_clients.tree_db_backend import PathResponse, ItemResponse, DriveResponse, ItemsResponse


async def get_remote_paths(
        remote_treedb: TreeDbClient,
        tree_items: ItemsResponse,
        context: Context
):
    items_path_ = await asyncio.gather(*[
        remote_treedb.get_path(item.itemId, headers=context.headers())
        for item in tree_items.items
    ])
    items_path = [PathResponse(**p) for p in items_path_]

    def is_borrowed(item: ItemResponse):
        return json.loads(item.metadata)['borrowed']

    owning_location = next((path for path in items_path if not is_borrowed(path.item)), None)
    borrowed_locations = [path for path in items_path if is_borrowed(path.item)]
    return owning_location, borrowed_locations


async def ensure_local_path(
        path_item: PathResponse,
        local_treedb: TreeDbClient,
        context: Context):
    async with context.start(action="ensure local path") as ctx:
        folders = path_item.folders
        try:
            if folders:
                await local_treedb.get_folder(folder_id=folders[-1].folderId, headers=ctx.headers())
            else:
                await local_treedb.get_drive(drive_id=path_item.drive.driveId, headers=ctx.headers())
        except HTTPException as e:
            if e.status_code == 404:
                if len(folders) <= 1:
                    await ensure_drive(path_item.drive, local_treedb, context=ctx)
                else:
                    await ensure_local_path(PathResponse(drive=path_item.drive, folders=folders[0:-1],
                                                         item=path_item.item),
                                            local_treedb,
                                            context=ctx)
                if not folders:
                    return
                folder = folders[-1]
                body = {"folderId": folder.folderId, "name": folder.name}
                await local_treedb.create_folder(parent_folder_id=folder.parentFolderId, body=body,
                                                 headers=context.headers())


async def ensure_drive(drive: DriveResponse, local_treedb: TreeDbClient, context: Context):
    try:
        await local_treedb.get_drive(drive_id=drive.driveId, headers=context.headers())
    except HTTPException as e:
        if e.status_code == 404:
            body = {"driveId": drive.driveId, "name": drive.name}
            await local_treedb.create_drive(group_id=drive.groupId, body=body, headers=context.headers())
            return
        raise e


async def get_local_owning_folder_id(
        owning_location: PathResponse,
        local_treedb: TreeDbClient,
        default_folder_id: str,
        context: Context
):
    if owning_location:
        await ensure_local_path(owning_location, local_treedb, context)

    return owning_location.folders[-1].folderId \
        if owning_location \
        else default_folder_id


async def sync_borrowed_items(
        asset_id: str,
        borrowed_locations: List[PathResponse],
        local_treedb: TreeDbClient,
        local_gtw: AssetsGatewayClient,
        context: Context
):
    await asyncio.gather(*[ensure_local_path(p, local_treedb, context) for p in borrowed_locations])

    await asyncio.gather(*[
        local_gtw.get_treedb_backend_router().borrow(
            item_id=asset_id,
            body={'targetId': p.item.itemId, 'destinationFolderId': p.folders[-1].folderId},
            headers=context.headers()
        )
        for p in borrowed_locations
    ])


async def sync_access_policies(
        asset_id: str,
        context: Context
):
    async with context.start(action="Sync. access policies") as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        assets_gtw = await RemoteClients.get_assets_gateway_client(remote_host=env.selectedRemote, context=ctx)
        assets_remote = assets_gtw.get_assets_backend_router()
        assets_local = LocalClients.get_assets_client(await ctx.get('env', YouwolEnvironment))
        access_info = await assets_remote.get_access_info(asset_id=asset_id, headers=ctx.headers())
        access_info = access_info['ownerInfo']
        await asyncio.gather(
            assets_local.put_access_policy(asset_id=asset_id, group_id="*", body=access_info['defaultAccess']),
            *[assets_local.put_access_policy(asset_id=asset_id, group_id=group['groupId'], body=group['access'])
              for group in access_info['exposingGroups']]
        )


T = TypeVar('T')


async def create_asset_local(
        asset_id: str,
        kind: str,
        default_owning_folder_id,
        get_raw_data: Callable[[Context], Awaitable[T]],
        post_raw_data: Optional[Callable[[str, T, Context], Awaitable[None]]],
        context: Context
        ):
    env = await context.get("env", YouwolEnvironment)
    async with context.start(
            action=f"Fetch asset {asset_id} of kind {kind}",
            ) as ctx:
        local_treedb: TreeDbClient = LocalClients.get_treedb_client(env)
        local_gtw: AssetsGatewayClient = LocalClients.get_assets_gateway_client(env)
        remote_gtw = await RemoteClients.get_assets_gateway_client(remote_host=env.selectedRemote, context=context)
        remote_treedb = remote_gtw.get_treedb_backend_router()
        remote_assets = remote_gtw.get_assets_backend_router()
        headers = ctx.headers()
        raw_data, metadata, tree_items = await asyncio.gather(
            get_raw_data(ctx),
            remote_assets.get_asset(asset_id=asset_id, headers=headers),
            remote_treedb.get_items_from_asset(asset_id=asset_id, headers=headers),
            return_exceptions=True
        )

        if isinstance(raw_data, Exception):
            await ctx.error(f"Can not fetch raw part of the asset")
            raise raw_data

        if isinstance(metadata, Exception):
            await ctx.error(f"Can not fetch asset's metadata")
            raise metadata

        if isinstance(tree_items, Exception):
            await ctx.error(f"Can not fetch tree-db items")
            raise tree_items

        raw_data = cast(Dict, raw_data)
        metadata = cast(Dict, metadata)
        tree_items = cast(Dict, tree_items)

        await ctx.info(text="Raw & meta data retrieved", data={
            "metadata": metadata,
            "tree_items": tree_items,
        })
        owning_location, borrowed_locations = await get_remote_paths(
            remote_treedb=remote_treedb,
            tree_items=ItemsResponse(**tree_items),
            context=ctx
        )
        await ctx.info(text="Explorer paths retrieved", data={
            "owning_location": owning_location.dict() if owning_location else "No owning location in available groups",
            "borrowed_locations": [p.dict() for p in borrowed_locations]
        })

        owning_folder_id = await get_local_owning_folder_id(
            owning_location=owning_location,
            local_treedb=local_treedb,
            default_folder_id=default_owning_folder_id,
            context=context
        )
        await ctx.info(text="Owning folder retrieved", data={
            "owning_folder_id": owning_folder_id
        })
        await post_raw_data(owning_folder_id, raw_data, ctx)

        await ctx.info(text="Asset raw's data downloaded successfully")
        await sync_access_policies(asset_id=asset_id, context=context)
        await sync_borrowed_items(
            asset_id=asset_id,
            borrowed_locations=borrowed_locations,
            local_treedb=local_treedb,
            local_gtw=local_gtw,
            context=ctx
        )
        await ctx.info(text="Borrowed items created successfully")
        # 'groupId' may not be the original one as it has changed if current user do not have access to it
        del metadata['groupId']
        # the next line is not fetching images
        resp = await local_gtw.get_assets_backend_router().update_asset(
            asset_id=asset_id, body=metadata,
            headers=ctx.headers()
        )
        print(resp)
        await ctx.info(text="Asset metadata uploaded successfully")
