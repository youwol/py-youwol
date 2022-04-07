import asyncio
import json

from fastapi import HTTPException
from youwol_assets_gateway.configurations import Configuration
from youwol_assets_gateway.raw_stores import AssetMeta
from youwol_assets_gateway.utils import raw_id_to_asset_id, to_asset_resp
from youwol_utils.context import Context
from youwol_utils.http_clients.assets_gateway import NewAssetResponse, PermissionsResponse


async def assert_read_permissions_from_raw_id(raw_id: str, configuration: Configuration, context: Context):
    assets_db = configuration.assets_client
    asset_id = raw_id_to_asset_id(raw_id)
    permissions = await assets_db.get_permissions(asset_id=asset_id, headers=context.headers())
    if not permissions['read']:
        raise HTTPException(status_code=403, detail=f"Unauthorized to access {raw_id}")


async def assert_write_permissions_from_raw_id(raw_id: str, configuration: Configuration, context: Context):
    assets_db = configuration.assets_client
    asset_id = raw_id_to_asset_id(raw_id)
    permissions = await assets_db.get_permissions(asset_id=asset_id, headers=context.headers())
    if not permissions['write']:
        raise HTTPException(status_code=403, detail=f"Unauthorized to write {raw_id}")


async def create_asset(
        kind: str,
        raw_id: str,
        folder_id: str,
        metadata: AssetMeta,
        context: Context,
        configuration: Configuration
):

    async with context.start(
            action='create asset',
            with_attributes={"raw_id": raw_id}
    ) as ctx:
        tree_db, assets_db = configuration.treedb_client, configuration.assets_client

        async with ctx.start(action="Retrieve treedb parent item") as ctx_1:
            try:
                parent = await tree_db.get_folder(folder_id=folder_id, headers=ctx_1.headers())
            except HTTPException:
                parent = await tree_db.get_drive(drive_id=folder_id, headers=ctx_1.headers())
            group_id = parent["groupId"]
            await ctx_1.info(text="Parent treedb item found", data=parent)

        asset_id = raw_id_to_asset_id(raw_id)
        body_asset = {
            "assetId": asset_id,
            "relatedId": raw_id,
            "kind": kind,
            "name": metadata.name or f"new {kind}",
            "description": metadata.description or "",
            "groupId": group_id,
            "tags": metadata.tags or []
        }

        async with ctx.start(action="Registration in assets_db") as ctx_1:
            # missing images e.g. when uploading an image as file we want the image to be a thumbnail
            await assets_db.create_asset(body=body_asset, headers=ctx_1.headers())
            images_coroutines = [
                assets_db.post_image(asset_id=asset_id, filename=image.name, src=image.content, headers=ctx_1.headers())
                for image in metadata.images
            ] if metadata.images else []
            await asyncio.gather(*images_coroutines)

        async with ctx.start(action="Get created asset", with_attributes={"asset_id": asset_id}) as ctx_1:
            asset = await assets_db.get(asset_id=asset_id, headers=ctx_1.headers())
            await ctx_1.info(text="Asset response", data=asset)

        body_tree = {
            "itemId": asset_id,
            "name": body_asset['name'],
            "type": kind,
            "relatedId": asset_id,
            "metadata": json.dumps({"assetId": asset_id, "relatedId": raw_id, "borrowed": False, })
        }

        async with ctx.start(action="Registration in tree_db", with_attributes={"folder_id": folder_id}) as ctx_1:
            resp_tree = await tree_db.create_item(folder_id=folder_id, body=body_tree, headers=ctx_1.headers())
            await ctx_1.info(text="Treedb response", data=resp_tree)

        response = NewAssetResponse(**{
            **to_asset_resp(asset, permissions=PermissionsResponse(read=True, write=True, share=True)).dict(),
            **{"treeId": resp_tree["itemId"]}
        })
        return response


async def delete_asset(
        raw_id: str,
        context: Context,
        configuration: Configuration
):
    async with context.start(
            action='delete asset',
            with_attributes={"raw_id": raw_id}
    ) as ctx:
        asset_id = raw_id_to_asset_id(raw_id)
        tree_db, assets_db = configuration.treedb_client, configuration.assets_client
        resp = await tree_db.get_items_from_related_id(related_id=asset_id, headers=ctx.headers())
        await asyncio.gather(*[tree_db.remove_item(item_id=item['item_id'], headers=ctx.headers())
                               for item in resp['items']])
        await assets_db.delete_asset(asset_id=asset_id, headers=ctx.headers())
