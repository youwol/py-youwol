import asyncio
from dataclasses import dataclass
from typing import Set
from fastapi import HTTPException
from auto_download.common import (
    get_remote_paths, get_local_owning_folder_id, sync_borrowed_items,
    create_asset_local,
    )
from auto_download.models import DownloadLogger, DownloadTask
from configuration.clients import RemoteClients, LocalClients
from context import Context
from services.backs.treedb.models import ItemsResponse
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.treedb.treedb import TreeDbClient


@dataclass
class DownloadDataTask(DownloadTask):

    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self):

        local_assets: AssetsClient = LocalClients.get_assets_client(context=self.context)
        try:
            await local_assets.get(asset_id=self.asset_id)
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            else:
                raise e

    async def create_local_asset(self):

        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        default_drive = await self.context.config.get_default_drive(context=self.context)

        await create_asset_local(
            asset_id=self.asset_id,
            kind='data',
            default_owning_folder_id=default_drive.downloadFolderId,
            get_raw_data=lambda: remote_gtw.get_raw(kind='data', raw_id=self.raw_id),
            to_post_raw_data=lambda data: {"file": data, "rawId": self.raw_id},
            context=self.context
            )


async def download_data(
        remote_gtw: AssetsGatewayClient,
        asset_id: str,
        raw_id: str,
        process_id: str,
        downloaded_ids: Set[str],
        context: Context,
        logger: DownloadLogger
        ):
    # <!> this point is reach either only the url responded with a 404 in local
    # => the version need to be fetched in local.
    #
    # From the point when the url responded with a 404, the project have been fetched by a way or another
    # => still needed to check for availability locally first.
    if raw_id in downloaded_ids:
        return
    downloaded_ids.add(raw_id)

    local_gtw: AssetsGatewayClient = context.config.localClients.assets_gateway_client
    local_treedb: TreeDbClient = context.config.localClients.treedb_client
    local_data: AssetsGatewayClient = context.config.localClients.assets_gateway_client
    remote_treedb = await RemoteClients.get_treedb_client(context)

    local_data, remote_data = await asyncio.gather(
        local_data.get_raw(kind='data', raw_id=raw_id),
        remote_gtw.get_raw(kind='data', raw_id=raw_id),
        return_exceptions=True
        )

    if not isinstance(local_data, Exception):
        return

    await logger.info(
        process_id=process_id,
        title=f"Proceed to data download of {raw_id}"
        )
    metadata, tree_items = await asyncio.gather(
        remote_gtw.get_asset_metadata(asset_id=asset_id),
        remote_treedb.get_items_from_related_id(related_id=asset_id)
        )

    owning_location, borrowed_locations = await get_remote_paths(
        remote_treedb=remote_treedb,
        tree_items=ItemsResponse(**tree_items)
        )
    default_folder_id = (await context.config.get_default_drive()).downloadFolderId
    owning_folder_id = await get_local_owning_folder_id(
        owning_location=owning_location,
        local_treedb=local_treedb,
        default_folder_id=default_folder_id
        )

    await local_gtw.put_asset_with_raw(
                kind='flux-project',
                folder_id=owning_folder_id,
                data=remote_data
                )
    await sync_borrowed_items(
        asset_id=asset_id,
        borrowed_locations=borrowed_locations,
        local_treedb=local_treedb,
        local_gtw=local_gtw
        )
    await logger.info(
        process_id=process_id,
        title=f"Data {raw_id} downloaded successfully"
        )
    print("\n\n")
