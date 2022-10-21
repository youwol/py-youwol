import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from starlette.requests import Request

from youwol_utils import to_group_scope, is_authorized_write
from youwol_utils.context import Context
from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.http_clients.assets_backend import PermissionsResp
from youwol_utils.http_clients.assets_gateway import (
    AssetResponse, OwnerInfo, ExposingGroup,
    ConsumerInfo, AccessInfo, OwningGroup, UpdateAssetBody
)
from youwol_assets_gateway.utils import to_asset_resp, format_policy

router = APIRouter(tags=["assets-gateway.assets"])


@router.get("/{asset_id}",
            response_model=AssetResponse,
            summary="get asset")
async def get(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[AssetResponse]
    async with Context.start_ep(
            request=request,
            response=lambda: response,
            action='get asset'
    ) as ctx:
        headers = ctx.headers()
        assets_client = configuration.assets_client
        asset, permissions = await asyncio.gather(
            assets_client.get(asset_id=asset_id, headers=headers),
            assets_client.get_permissions(asset_id=asset_id, headers=headers)
        )
        response = to_asset_resp(asset=asset, permissions=permissions)
        return response


@router.get("/location/{tree_id}",
            response_model=AssetResponse,
            summary="get an asset")
async def get_asset_by_tree_id(
        request: Request,
        tree_id: str,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[AssetResponse]
    async with Context.start_ep(
            action='Get asset by tree id',
            request=request,
            response=lambda: response
    ) as ctx:
        tree_db, assets_db = configuration.treedb_client, configuration.assets_client

        async with ctx.start(action="Get treedb item") as ctx_1:
            tree_item = await tree_db.get_item(item_id=tree_id, headers=ctx_1.headers())
            await ctx_1.info(text="Treedb item", data=tree_item)
        asset_id = tree_item['assetId']

        async with ctx.start(action="Get asset") as ctx_1:
            asset = await assets_db.get(asset_id=asset_id, headers=ctx_1.headers())

        response = to_asset_resp(asset)
        return response


@router.post("/{asset_id}",
             response_model=AssetResponse,
             summary="get asset")
async def update_asset(
        request: Request,
        asset_id: str,
        body: UpdateAssetBody,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[AssetResponse]
    async with Context.start_ep(
            action='update asset',
            request=request,
            response=lambda: response,
            with_attributes={"asset_id": asset_id}
    ) as ctx:
        # The next line provide a way to re-use the body of the request latter on in a middleware if needed
        request.state.body = body
        assets_client, treedb_client = configuration.assets_client, configuration.treedb_client
        async with ctx.start(action="get asset") as ctx_1:
            asset = await assets_client.get(asset_id=asset_id, headers=ctx_1.headers())

        await ctx.info(text="Successfully retrieved asset", data={"asset": asset})

        async with ctx.start(action="get treedb items from asset id") as ctx_1:
            items_tree = await treedb_client.get_items_from_asset(asset_id=asset_id, headers=ctx_1.headers())
            await ctx_1.info("Retrieved treedb items from assetId", data=items_tree)
            if not items_tree['items']:
                raise HTTPException(status_code=404, detail="tree item not found")

        body_asset = {**asset, **{k: v for k, v in body.dict().items() if v is not None}}

        async with ctx.start(action="update asset part") as ctx_asset:
            resp_asset = await assets_client.update_asset(asset_id=asset_id, body=body_asset,
                                                          headers=ctx_asset.headers())
            await ctx_asset.info("Response", data=resp_asset)

        async with ctx.start(action="sync treedb_items") as ctx_tree:
            coroutines_tree = [treedb_client.update_item(item_id=item['itemId'], body={"name": body.name},
                                                         headers=ctx_tree.headers())
                               for item in items_tree['items']]
            resp_tree = await asyncio.gather(*coroutines_tree)
            await ctx_tree.info("Response", data={"responses": resp_tree})

        return to_asset_resp(body_asset)


@router.get("/{asset_id}/access",
            response_model=AccessInfo,
            summary="get asset info w/ access")
async def access_info(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    response = Optional[AccessInfo]
    async with Context.start_ep(
            action='retrieve access info',
            request=request,
            response=lambda: response,
            with_attributes={"asset_id": asset_id}
    ) as ctx:
        assets_client, treedb = configuration.assets_client, configuration.treedb_client
        asset, permissions = await asyncio.gather(
            assets_client.get(asset_id=asset_id, headers=ctx.headers()),
            assets_client.get_permissions(asset_id=asset_id, headers=ctx.headers())
        )
        owner_info = None
        if is_authorized_write(request, asset['groupId']):
            resp = await treedb.get_items_from_asset(asset_id=asset_id, headers=ctx.headers())
            groups = list({item['groupId'] for item in resp['items'] if item['groupId'] != asset["groupId"]})
            policies = await asyncio.gather(*[
                assets_client.get_access_policy(asset_id=asset_id, group_id=group_id, headers=ctx.headers())
                for group_id in groups + ["*"]
            ])
            exposing_groups = [ExposingGroup(name=to_group_scope(group), groupId=group, access=format_policy(policy))
                               for group, policy in zip(groups, policies[0:-1])]
            default_access = format_policy(policies[-1])
            owner_info = OwnerInfo(exposingGroups=exposing_groups, defaultAccess=default_access)

        permissions = PermissionsResp(write=permissions['write'], read=permissions['read'], share=permissions["share"],
                                      expiration=permissions['expiration'])
        consumer_info = ConsumerInfo(permissions=permissions)
        response = AccessInfo(owningGroup=OwningGroup(name=to_group_scope(asset['groupId']), groupId=asset['groupId']),
                              ownerInfo=owner_info, consumerInfo=consumer_info)
        return response
