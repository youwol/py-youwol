import asyncio
import json
from typing import Mapping, Dict

from aiohttp import FormData, ClientSession
from starlette.requests import Request
from fastapi import HTTPException, WebSocket

from configuration import YouwolConfiguration, RemoteClients
from configurations import configuration
from routers.commands.upload_assets.data import UploadDataTask
from routers.commands.upload_assets.flux_project import UploadFluxProjectTask
from routers.commands.upload_assets.models import UploadTask
from routers.commands.upload_assets.package import UploadPackageTask
from routers.commands.upload_assets.story import UploadStoryTask
from services.backs.treedb.models import PathResponse
from youwol.configuration import parse_json
from youwol.utils_low_level import to_json
from youwol.models import ActionStep
from youwol.routers.commons import local_path, ensure_path
from youwol.context import Context
from youwol_utils import decode_id, JSON
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.treedb.treedb import TreeDbClient


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

        path_item = local_path(tree_id=tree_id, config=context.config)
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


async def synchronize_metadata(asset_id: str, assets_gtw_client: AssetsGatewayClient, context: Context):

    local_assets_gtw: AssetsGatewayClient = context.config.localClients.assets_gateway_client

    local_metadata, remote_metadata = await asyncio.gather(
        local_assets_gtw.get_asset_metadata(asset_id=asset_id),
        assets_gtw_client.get_asset_metadata(asset_id=asset_id)
        )
    missing_images_urls = [p for p in local_metadata['images'] if p not in remote_metadata['images']]
    full_urls = [f"http://localhost:{configuration.http_port}{url}" for url in missing_images_urls]
    filenames = [url.split('/')[-1] for url in full_urls]

    await context.info(
        step=ActionStep.RUNNING,
        content="Synchronise metadata",
        json={
            'local_metadata': local_metadata,
            'remote_metadata': remote_metadata,
            'missing images': full_urls
            }
        )

    async def download_img(session: ClientSession, url: str):
        async with await session.get(url=url) as resp:
            if resp.status == 200:
                return await resp.read()

    async with ClientSession() as http_session:
        images_data = await asyncio.gather(*[download_img(http_session, url) for url in full_urls])

    forms = []
    for filename, value in zip(filenames, images_data):
        form_data = FormData()
        form_data.add_field(name='file', value=value, filename=filename)
        forms.append(form_data)

    await asyncio.gather(
        assets_gtw_client.update_asset(asset_id=asset_id, body=local_metadata),
        *[
            assets_gtw_client.post_asset_image(asset_id=asset_id, filename=name, data=form)
            for name, form in zip(filenames, forms)
            ]
        )


async def upload_asset(
        request: Request,
        body: JSON,
        config: YouwolConfiguration,
        web_socket: WebSocket
        ):
    upload_factories: Dict[str, any] = {
        "data": UploadDataTask,
        "flux-project": UploadFluxProjectTask,
        "story": UploadStoryTask,
        "package": UploadPackageTask
        }

    asset_id = body['assetId']
    context = Context(config=config, request=request, web_socket=web_socket)
    local_treedb: TreeDbClient = config.localClients.treedb_client
    local_assets: AssetsClient = config.localClients.assets_client

    async with context.start(
            f"Upload asset {asset_id}",
            ) as ctx:

        raw_id = decode_id(asset_id)
        asset, tree_item = await asyncio.gather(
            local_assets.get(asset_id=asset_id),
            local_treedb.get_item(item_id=asset_id)
            )
        factory: UploadTask = upload_factories[asset['kind']](
            raw_id=raw_id,
            asset_id=asset_id,
            context=context
            )

        local_data = await factory.get_raw()
        path_item = await local_treedb.get_path(item_id=tree_item['itemId'])
        await ctx.info(
            step=ActionStep.STATUS,
            content="Data retrieved",
            json={"path_item": path_item, "raw data": local_data}
            )

        assets_gtw_client = await RemoteClients.get_assets_gateway_client(context=context)

        await ensure_path(path_item=PathResponse(**path_item), assets_gateway_client=assets_gtw_client)
        try:
            await assets_gtw_client.get_asset_metadata(asset_id=asset_id)
            await ctx.info(
                step=ActionStep.STATUS,
                content="Asset already found in deployed environment"
                )
            await factory.update_raw(data=local_data, folder_id=tree_item['folderId'])
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            await ctx.info(
                step=ActionStep.RUNNING,
                content="Project not already found => start creation"
                )
            await factory.create_raw(data=local_data, folder_id=tree_item['folderId'])
            # local_flux_app['projectId'] = raw_id

        await synchronize_permissions_metadata_symlinks(
            asset_id=asset_id,
            tree_id=tree_item['itemId'],
            assets_gtw_client=assets_gtw_client,
            context=ctx
            )

    return {}
