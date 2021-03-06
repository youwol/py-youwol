import asyncio
import json
from typing import Mapping, Dict, cast, Optional, Any

from aiohttp import FormData, ClientSession
from fastapi import HTTPException

from youwol_utils.http_clients.tree_db_backend import PathResponse
from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.commons import Label
from youwol.routers.commons import local_path, ensure_path
from youwol.routers.environment.upload_assets.data import UploadDataTask
from youwol.routers.environment.upload_assets.flux_project import UploadFluxProjectTask
from youwol.routers.environment.upload_assets.models import UploadTask
from youwol.routers.environment.upload_assets.package import UploadPackageTask
from youwol.routers.environment.upload_assets.story import UploadStoryTask
from youwol_utils import decode_id
from youwol_utils import to_json
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json


async def synchronize_permissions_metadata_symlinks(
        asset_id: str,
        tree_id: str,
        assets_gtw_client: AssetsGatewayClient,
        context: Context
        ):

    await asyncio.gather(
        create_borrowed_items(asset_id=asset_id, tree_id=tree_id, assets_gtw_client=assets_gtw_client,
                              context=context),
        synchronize_permissions(assets_gtw_client=assets_gtw_client, asset_id=asset_id, context=context),
        synchronize_metadata(asset_id=asset_id, assets_gtw_client=assets_gtw_client, context=context)
        )


async def synchronize_permissions(assets_gtw_client: AssetsGatewayClient, asset_id: str, context: Context):
    async with context.start(
            action="synchronize_permissions",
            with_attributes={
                'assetId': asset_id
            }
    ) as ctx:  # type: Context
        env = await context.get('env', YouwolEnvironment)
        local_assets_gtw = LocalClients.get_assets_gateway_client(env=env)
        access_info = await local_assets_gtw.get_asset_access(asset_id=asset_id, headers=ctx.headers())
        await ctx.info(
            labels=[str(Label.RUNNING)],
            text="Permissions retrieved",
            data={"access_info": access_info}
        )
        default_permission = access_info["ownerInfo"]["defaultAccess"]
        groups = access_info["ownerInfo"]["exposingGroups"]
        await asyncio.gather(
            assets_gtw_client.put_asset_access(asset_id=asset_id, group_id='*', body=default_permission,
                                               headers=ctx.headers()),
            *[
                assets_gtw_client.put_asset_access(asset_id=asset_id, group_id=g['groupId'], body=g['access'],
                                                   headers=ctx.headers())
                for g in groups
            ]
        )


async def create_borrowed_items(asset_id: str, tree_id: str, assets_gtw_client: AssetsGatewayClient, context: Context):

    env = await context.get('env', YouwolEnvironment)
    async with context.start(
            action="create_borrowed_items",
            with_attributes={
                'assetId': asset_id,
                'treeId': tree_id
                }
            ) as ctx:

        items_treedb = parse_json(env.pathsBook.local_treedb_docdb)
        tree_items = [item for item in items_treedb['documents'] if item['related_id'] == asset_id]
        borrowed_items = [item for item in tree_items if json.loads(item['metadata'])['borrowed']]

        await asyncio.gather(*[
            create_borrowed_item(item=item, borrowed_tree_id=tree_id, assets_gtw_client=assets_gtw_client,
                                 context=ctx)
            for item in borrowed_items
            ])


async def create_borrowed_item(borrowed_tree_id: str, item: Mapping[str, any], assets_gtw_client: AssetsGatewayClient,
                               context: Context):
    async with context.start(
            action="create_borrowed_items",
            with_attributes={
                'borrowed_tree_id': borrowed_tree_id,
                'tree_id': item["item_id"]
            }
    ) as ctx:  # type: Context

        tree_id = item["item_id"]
        try:
            await assets_gtw_client.get_tree_item(item_id=tree_id, headers=ctx.headers())
            return
        except HTTPException as e:
            if e.status_code != 404:
                raise e

            path_item = await local_path({"treeId": tree_id}, context=ctx)
            path_item = PathResponse(**path_item)
            await ctx.info(
                labels=[Label.RUNNING],
                text="Borrowed tree item not found, start creation",
                data={"treeItemPath": to_json(path_item)}
            )
            await ensure_path(path_item=path_item, assets_gateway_client=assets_gtw_client, context=ctx)
            parent_id = path_item.drive.driveId
            if len(path_item.folders) > 0:
                parent_id = path_item.folders[0].folderId

        await assets_gtw_client.borrow_tree_item(tree_id=borrowed_tree_id,
                                                 body={
                                                     "itemId": tree_id,
                                                     "destinationFolderId": parent_id
                                                 },
                                                 headers=ctx.headers()
                                                 )
        await ctx.info(text="Borrowed item created")


async def synchronize_metadata(asset_id: str, assets_gtw_client: AssetsGatewayClient, context: Context):
    env = await context.get('env', YouwolEnvironment)
    async with context.start(
            action="synchronize_metadata",
            with_attributes={
                'asset_id': asset_id
            }
    ) as ctx:  # type: Context

        local_assets_gtw: AssetsGatewayClient = LocalClients.get_assets_gateway_client(env=env)

        local_metadata, remote_metadata = await asyncio.gather(
            local_assets_gtw.get_asset_metadata(asset_id=asset_id, headers=ctx.headers()),
            assets_gtw_client.get_asset_metadata(asset_id=asset_id, headers=ctx.headers())
        )
        missing_images_urls = [p for p in local_metadata['images'] if p not in remote_metadata['images']]
        full_urls = [f"http://localhost:{env.httpPort}{url}" for url in missing_images_urls]
        filenames = [url.split('/')[-1] for url in full_urls]

        await ctx.info(
            labels=[str(Label.RUNNING)],
            text="Synchronise metadata",
            data={
                'local_metadata': local_metadata,
                'remote_metadata': remote_metadata,
                'missing images': full_urls
            }
        )

        async def download_img(session: ClientSession, url: str):
            async with await session.get(url=url, headers=ctx.headers()) as resp:
                if resp.status == 200:
                    return await resp.read()

        async with ClientSession() as http_session:
            images_data = await asyncio.gather(*[download_img(http_session, url) for url in full_urls])

        forms = []
        for filename, value in zip(filenames, images_data):
            form_data = FormData()
            form_data.add_field(name='file', value=value, filename=filename)
            forms.append(form_data)
        remote_assets = await RemoteClients.get_gtw_assets_client(context=context)
        await asyncio.gather(
            remote_assets.update_asset(asset_id=asset_id, body=local_metadata, headers=ctx.headers()),
            *[
                assets_gtw_client.post_asset_image(asset_id=asset_id, filename=name, data=form, headers=ctx.headers())
                for name, form in zip(filenames, forms)
            ]
        )


async def upload_asset(
        asset_id: str,
        options: Optional[Any],
        context: Context
):
    upload_factories: Dict[str, any] = {
        "data": UploadDataTask,
        "flux-project": UploadFluxProjectTask,
        "story": UploadStoryTask,
        "package": UploadPackageTask
        }

    async with context.start(
            action="upload_asset",
            with_attributes={
                'asset_id': asset_id
            }
    ) as ctx:  # type: Context

        env = await context.get('env', YouwolEnvironment)
        local_treedb: TreeDbClient = LocalClients.get_treedb_client(env=env)
        local_assets: AssetsClient = LocalClients.get_assets_client(env=env)
        raw_id = decode_id(asset_id)
        asset, tree_item = await asyncio.gather(
            local_assets.get(asset_id=asset_id, headers=ctx.headers()),
            local_treedb.get_item(item_id=asset_id, headers=ctx.headers()),
            return_exceptions=True
        )
        if isinstance(asset, HTTPException) and asset.status_code == 404:
            await ctx.error(text="Can not find the asset in the local assets store")
            raise RuntimeError("Can not find the asset in the local assets store")
        if isinstance(tree_item, HTTPException) and tree_item.status_code == 404:
            await ctx.error(text="Can not find the tree item in the local treedb store")
            raise RuntimeError("Can not find the tree item in the local treedb store")
        if isinstance(asset, Exception) or isinstance(tree_item, Exception):
            raise RuntimeError("A problem occurred while fetching the local asset/tree items")

        await ctx.info(text="Asset & treedb item retrieved",
                       data={"treedbItem": tree_item, "asset": asset}
                       )
        asset = cast(Dict, asset)
        tree_item = cast(Dict, tree_item)

        factory: UploadTask = upload_factories[asset['kind']](
            raw_id=raw_id,
            asset_id=asset_id,
            options=options
        )

        local_data = await factory.get_raw(context=ctx)
        try:
            path_item = await local_treedb.get_path(item_id=tree_item['itemId'], headers=ctx.headers())
        except HTTPException as e:
            if e.status_code == 404:
                await ctx.error(text=f"Can not get path of item with id '{tree_item['itemId']}'",
                                data={"tree_item": tree_item, "error_detail": e.detail})
            raise e

        await ctx.info(
            text="Data retrieved",
            data={"path_item": path_item, "raw data": local_data}
        )

        assets_gtw_client = await RemoteClients.get_assets_gateway_client(context=ctx)

        await ensure_path(path_item=PathResponse(**path_item), assets_gateway_client=assets_gtw_client, context=ctx)
        try:
            await assets_gtw_client.get_asset_metadata(asset_id=asset_id, headers=ctx.headers())
            await assets_gtw_client.get_tree_item(tree_item['itemId'], headers=ctx.headers())
            await ctx.info(
                text="Asset already found in deployed environment"
            )
            await factory.update_raw(data=local_data, folder_id=tree_item['folderId'], context=ctx)
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            await ctx.info(
                labels=[Label.RUNNING],
                text="Asset not already found => start creation"
            )
            await factory.create_raw(data=local_data, folder_id=tree_item['folderId'], context=ctx)

        await synchronize_permissions_metadata_symlinks(
            asset_id=asset_id,
            tree_id=tree_item['itemId'],
            assets_gtw_client=assets_gtw_client,
            context=ctx
            )

    return {}
