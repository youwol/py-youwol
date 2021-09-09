import asyncio
import json
from typing import Mapping

from fastapi import HTTPException

from youwol.configuration import parse_json
from youwol.utils_low_level import to_json
from youwol.models import ActionStep
from youwol.routers.commons import local_path, ensure_path
from youwol.context import Context
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


async def synchronize_permissions(assets_gtw_client: AssetsGatewayClient, asset_id: str, context: Context):

    local_assets_gtw = context.config.localClients.assets_gateway_client
    access_info = await local_assets_gtw.get_asset_access(asset_id=asset_id)
    await context.info(
        step=ActionStep.RUNNING,
        content="Permissions retrieved",
        json={"access_info": access_info}
        )
    default_permission = access_info["ownerInfo"]["defaultAccess"]
    groups = access_info["ownerInfo"]["exposingGroups"]
    await asyncio.gather(
        assets_gtw_client.put_asset_access(asset_id=asset_id, group_id='*', body=default_permission),
        *[
            assets_gtw_client.put_asset_access(asset_id=asset_id, group_id=g['groupId'], body=g['access'])
            for g in groups
            ]
        )


async def create_borrowed_items(asset_id: str, tree_id: str, assets_gtw_client: AssetsGatewayClient, context: Context):

    items_treedb = parse_json(context.config.pathsBook.local_treedb_docdb)
    tree_items = [item for item in items_treedb['documents'] if item['related_id'] == asset_id]
    borrowed_items = [item for item in tree_items if json.loads(item['metadata'])['borrowed']]

    await asyncio.gather(*[
        create_borrowed_item(item=item, borrowed_tree_id=tree_id, assets_gtw_client=assets_gtw_client, context=context)
        for item in borrowed_items
        ])


async def create_borrowed_item(borrowed_tree_id: str, item: Mapping[str, any], assets_gtw_client: AssetsGatewayClient,
                               context: Context):

    tree_id = item["item_id"]
    try:
        await assets_gtw_client.get_tree_item(item_id=tree_id)
        return
    except HTTPException as e:
        if e.status_code != 404:
            raise e

        path_item = await local_path(tree_id=tree_id, config=context.config)
        await context.info(
            step=ActionStep.RUNNING,
            content="Borrowed tree item not found, start creation",
            json={"treeItemPath": to_json(path_item)}
            )
        await ensure_path(path_item, assets_gtw_client)
        parent_id = path_item.drive.driveId
        if len(path_item.folders) > 0:
            parent_id = path_item.folders[0].folderId

    await assets_gtw_client.borrow_tree_item(tree_id=borrowed_tree_id,
                                             body={
                                                 "itemId": tree_id,
                                                 "destinationFolderId": parent_id
                                                }
                                             )
    await context.info(step=ActionStep.DONE, content="Borrowed item created")
