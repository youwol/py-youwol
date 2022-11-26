import asyncio
from typing import Awaitable, Protocol

from fastapi import HTTPException

from youwol.environment import RemoteClients, LocalClients, YouwolEnvironment
from youwol_utils import YouwolHeaders
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import Context
from youwol_utils.http_clients.tree_db_backend import PathResponse, ItemResponse, DriveResponse


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


async def sync_asset_data(
        asset_id: str,
        remote_gtw: AssetsGatewayClient,
        context: Context
):
    async with context.start(action="Sync. asset data") as ctx:  # type: Context

        assets_remote = remote_gtw.get_assets_backend_router()
        assets_local = LocalClients.get_assets_client(await ctx.get('env', YouwolEnvironment))
        metadata = await assets_remote.get_asset(asset_id=asset_id, headers=ctx.headers())

        await assets_local.create_asset(body=metadata, headers=ctx.headers())

        access_info = await assets_remote.get_access_info(asset_id=asset_id, headers=ctx.headers())
        access_info = access_info['ownerInfo']
        await asyncio.gather(
            assets_local.put_access_policy(asset_id=asset_id, group_id="*", body=access_info['defaultAccess']),
            *[assets_local.put_access_policy(asset_id=asset_id, group_id=group['groupId'], body=group['access'])
              for group in access_info['exposingGroups']]
        )


async def sync_explorer_data(asset_id: str, remote_gtw: AssetsGatewayClient, context: Context):

    env = await context.get("env", YouwolEnvironment)

    async with context.start(action="Sync. explorer data") as ctx:  # type: Context
        remote_treedb = remote_gtw.get_treedb_backend_router()
        local_treedb = LocalClients.get_treedb_client(env)
        remote_item = await remote_treedb.get_item(item_id=asset_id, headers=ctx.headers())
        remote_item = ItemResponse(**remote_item)
        path_item = await remote_treedb.get_path(remote_item.itemId, headers=context.headers())
        path_item = PathResponse(**path_item)
        await ensure_local_path(path_item=path_item, local_treedb=local_treedb, context=ctx)

        body = {
            "name": remote_item.name,
            "kind": remote_item.kind,
            "itemId": remote_item.itemId,
            "borrowed": remote_item.borrowed,
            "assetId": remote_item.assetId,
            "metadata": remote_item.metadata
        }
        await local_treedb.create_item(folder_id=remote_item.folderId, body=body,
                                       headers={**ctx.headers(), YouwolHeaders.muted_http_errors: ""})


class SyncRawDataCallableType(Protocol):
    def __call__(self, asset_id: str, remote_gtw: AssetsGatewayClient, caller_context: Context) -> Awaitable[None]: ...


async def create_asset_local(
        asset_id: str,
        kind: str,
        sync_raw_data: SyncRawDataCallableType,
        context: Context
        ):
    async with context.start(
            action=f"Sync. asset {asset_id} of kind {kind}",
            ) as ctx:

        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        remote_gtw = await RemoteClients.get_assets_gateway_client(remote_host=env.currentAccess.host, context=context)
        await sync_raw_data(asset_id=asset_id, remote_gtw=remote_gtw, caller_context=ctx)
        await sync_explorer_data(asset_id=asset_id, remote_gtw=remote_gtw, context=ctx)
        await sync_asset_data(asset_id=asset_id, remote_gtw=remote_gtw, context=ctx)

        await ctx.info(text="Asset metadata uploaded successfully")
