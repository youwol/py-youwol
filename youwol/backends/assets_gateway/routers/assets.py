import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from starlette.requests import Request

from youwol_utils import (
    generate_headers_downstream, to_group_scope, itertools, is_authorized_write, AccessPolicyBody, PermissionsResp,
)
from youwol_utils.context import Context
from ..configurations import Configuration, get_configuration
from ..models import (
    AssetResponse, AssetsResponse, ImportAssetsBody, NewAssetResponse, QueryFlatBody, OwnerInfo, ExposingGroup,
    ConsumerInfo, AccessInfo, OwningGroup, UpdateAssetBody, QueryTreeBody, ItemsResponse, PermissionsResponse
)
from ..raw_stores.interface import AssetMeta
from ..utils import (
    to_item_resp, to_asset_meta, to_asset_resp, get_items_rec, get_items, format_policy,
    raw_id_to_asset_id,
)

router = APIRouter()


@router.post("/query-flat",
             response_model=AssetsResponse,
             summary="flat query of all assets")
async def query_flat(
        request: Request,
        body: QueryFlatBody,
        configuration: Configuration = Depends(get_configuration)
):
    headers = generate_headers_downstream(request.headers)
    resp = await configuration.assets_client.query(body=body.dict(), headers=headers)
    assets = [to_asset_resp(asset) for asset in resp["assets"]]
    return AssetsResponse(assets=assets)


@router.post("/query-tree",
             response_model=AssetsResponse,
             summary="query assets w/ tree structure")
async def query_tree(
        request: Request,
        body: QueryTreeBody,
        configuration: Configuration = Depends(get_configuration)):
    headers = generate_headers_downstream(request.headers)
    assets_client = configuration.assets_client
    items = \
        await get_items_rec(folder_id=body.folderId, headers=headers, configuration=configuration) \
            if body.recursive else \
            await get_items(folder_id=body.folderId, headers=headers, configuration=configuration)

    async def get_asset(item):
        metadata = json.loads(item['metadata'])
        return await assets_client.get(asset_id=metadata['assetId'], headers=headers)

    assets = await asyncio.gather(*[get_asset(item) for item in items])

    resp = AssetsResponse(assets=[to_asset_resp(asset) for asset, item in zip(assets, items)])
    return resp


@router.post("/register-in-tree",
             response_model=ItemsResponse,
             summary="import a 'dandling' asset")
async def import_treedb(
        request: Request,
        body: ImportAssetsBody,
        configuration: Configuration = Depends(get_configuration)):
    headers = generate_headers_downstream(request.headers)
    assets_db, tree_db = configuration.assets_client, configuration.treedb_client
    assets_stores = configuration.assets_stores()

    folder, *assets = await asyncio.gather(
        tree_db.get_folder(folder_id=body.folderId, headers=headers),
        *[assets_db.get(asset_id=asset_id, headers=headers) for asset_id in body.assetIds]
    )
    scope = to_group_scope(folder['groupId'])

    def harmonize_body_asset(asset_resp):
        return {
            "name": asset_resp["name"],
            "tags": asset_resp["tags"],
            "description": asset_resp["description"],
            "scope": scope
        }

    await asyncio.gather(*[assets_db.update_asset(asset_id=asset["assetId"], body=harmonize_body_asset(asset),
                                                  headers=headers)
                           for asset in assets])

    coroutines = []
    all_assets = sorted(assets, key=lambda asset: asset['kind'])

    def to_metadata(asset_resp):
        return AssetMeta(name=asset_resp['name'], description=asset_resp['description'], kind=asset_resp['kind'],
                         groupId=folder['groupId'], tags=asset_resp['tags'])

    for kind, group in itertools.groupby(all_assets, lambda asset: asset['kind']):
        store = next(store for store in assets_stores if store.path_name == kind)
        coroutines = coroutines + \
                     [store.sync_asset_metadata(request=request, raw_id=asset['relatedId'], metadata=to_metadata(asset),
                                                headers=headers) for asset in group]
    await asyncio.gather(*coroutines)

    def to_body_treedb(asset):
        return {
            "name": asset['name'],
            "type": asset['kind'],
            "relatedId": asset["assetId"],
            "metadata": json.dumps({"assetId": asset["assetId"], "relatedId": asset["relatedId"], "borrowed": False})
        }

    creates = [tree_db.create_item(folder_id=body.folderId, body=to_body_treedb(asset), headers=headers)
               for asset in assets]
    items = await asyncio.gather(*creates)

    return ItemsResponse(items=[to_item_resp(item) for item in items])


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


@router.put("/{kind}/location/{folder_id}",
            response_model=NewAssetResponse,
            summary="create an asset with initial raw content")
async def put_asset_with_raw_0(
        request: Request,
        kind: str,
        folder_id: str,
        group_id: str = Query(None, alias="group-id"),
        configuration: Configuration = Depends(get_configuration)):
    return await put_asset_with_raw(request=request, kind=kind, folder_id=folder_id, rest_of_path="", group_id=group_id,
                                    configuration=configuration)


@router.put("/{kind}/location/{folder_id}/{rest_of_path:path}",
            response_model=NewAssetResponse,
            summary="create an asset with initial raw content")
async def put_asset_with_raw_1(
        request: Request,
        kind: str,
        folder_id: str,
        rest_of_path: str,
        group_id: str = Query(None, alias="group-id"),
        configuration: Configuration = Depends(get_configuration)):
    return await put_asset_with_raw(request=request, kind=kind, folder_id=folder_id, rest_of_path=rest_of_path,
                                    group_id=group_id, configuration=configuration)


async def put_asset_with_raw(
        request: Request,
        kind: str,
        folder_id: str,
        rest_of_path: str,
        group_id: str = Query(None, alias="group-id"),
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[NewAssetResponse]
    async with Context.start_ep(
            request=request,
            response=lambda: response,
            action='create asset with raw data'
    ) as ctx:

        assets_stores = configuration.assets_stores()
        store = next(store for store in assets_stores if kind == store.path_name)

        tree_db, assets_db = configuration.treedb_client, configuration.assets_client

        if not group_id:
            async with ctx.start(action="Retrieve parent treedb item") as ctx_1:
                try:
                    parent = await tree_db.get_folder(folder_id=folder_id, headers=ctx_1.headers())
                except HTTPException:
                    parent = await tree_db.get_drive(drive_id=folder_id, headers=ctx_1.headers())
                group_id = parent["groupId"]
                await ctx_1.info(text="Parent treedb item found", data=parent)

        metadata = AssetMeta(name=f"new {kind}", description="", kind=kind, groupId=group_id, tags=[])

        async with ctx.start(action="Create raw part of the asset") as ctx_1:
            raw_id, meta_new = await store.create_asset(request=request, metadata=metadata, rest_of_path=rest_of_path,
                                                        headers=ctx_1.headers())

        asset_id = raw_id_to_asset_id(raw_id)
        body_asset = {
            "assetId": asset_id,
            "relatedId": raw_id,
            "kind": kind,
            "name": metadata.name if not meta_new.name else meta_new.name,
            "description": metadata.description if not meta_new.description else meta_new.description,
            "groupId": group_id,
            "tags": []
        }

        async with ctx.start(action="Register new asset in assets_db") as ctx_1:
            asset = await assets_db.create_asset(body=body_asset, headers=ctx_1.headers())
            images_coroutines = [
                assets_db.post_image(asset_id=asset_id, filename=image.name, src=image.content, headers=ctx_1.headers())
                for image in meta_new.images
            ] if meta_new.images else []
            await asyncio.gather(*images_coroutines)

        asset_id = asset['assetId']

        body_tree = {"itemId": asset_id,
                     "name": body_asset['name'],
                     "type": kind,
                     "relatedId": asset_id,
                     "metadata": json.dumps({"assetId": asset_id, "relatedId": raw_id, "borrowed": False, })}

        async with ctx.start(action="Register new asset in tree_db", with_attributes={"folder_id": folder_id}) as ctx_1:
            resp_tree = await tree_db.create_item(folder_id=folder_id, body=body_tree, headers=ctx_1.headers())
            await ctx_1.info(text="Treedb response", data=resp_tree)

        async with ctx.start(action="Get created asset", with_attributes={"asset_id": asset_id}) as ctx_1:
            asset = await assets_db.get(asset_id=asset_id, headers=ctx_1.headers())
            await ctx_1.info(text="Asset response", data=asset)

        response = NewAssetResponse(**{
            **to_asset_resp(asset, permissions=PermissionsResponse(read=True, write=True, share=True)).dict(),
            **{"treeId": resp_tree["itemId"]}
        })
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
        asset_id = tree_item['relatedId']

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
        assets_stores = configuration.assets_stores()
        async with ctx.start(action="get asset") as ctx_1:
            asset = await assets_client.get(asset_id=asset_id, headers=ctx_1.headers())

        store = next(store for store in assets_stores if store.path_name == asset['kind'])

        async with ctx.start(action="get treedb items from related id") as ctx_1:
            items_tree = await treedb_client.get_items_from_related_id(related_id=asset_id, headers=ctx_1.headers())
            if not items_tree['items']:
                raise HTTPException(status_code=404, detail="tree item not found")

        coroutines_tree = [treedb_client.update_item(item_id=item['itemId'], body={"name": body.name},
                                                     headers=ctx.headers())
                           for item in items_tree['items']]

        body = {**asset, **{k: v for k, v in body.dict().items() if v is not None}}
        await asyncio.gather(
            *coroutines_tree,
            assets_client.update_asset(asset_id=asset_id, body=body, headers=ctx.headers()),
            store.sync_asset_metadata(request=request, raw_id=asset['relatedId'], metadata=to_asset_meta(body),
                                      headers=ctx.headers())
        )
        return to_asset_resp(body)


@router.post("/{asset_id}/images/{filename}",
             response_model=AssetResponse,
             summary="get asset")
async def post_image(
        request: Request,
        asset_id: str,
        filename: str,
        file: UploadFile = File(...),
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[AssetResponse]
    async with Context.start_ep(
            action='post image of asset',
            request=request,
            response=lambda: response,
            with_attributes={"asset_id": asset_id}
    ) as ctx:
        assets_client = configuration.assets_client
        await assets_client.post_image(asset_id=asset_id, filename=filename, src=await file.read(),
                                       headers=ctx.headers())
        asset = await assets_client.get(asset_id=asset_id, headers=ctx.headers())
        response = to_asset_resp(asset)
        return response


@router.delete("/{asset_id}/images/{filename}",
               response_model=AssetResponse,
               summary="get asset")
async def remove_image(
        request: Request,
        asset_id: str,
        filename: str,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[AssetResponse]
    async with Context.start_ep(
            action='remove image of asset',
            request=request,
            response=lambda: response,
            with_attributes={"asset_id": asset_id, "filename": filename}
    ) as ctx:
        assets_client = configuration.assets_client

        await assets_client.remove_image(asset_id=asset_id, filename=filename, headers=ctx.headers())
        asset = await assets_client.get(asset_id=asset_id, headers=ctx.headers())

        return to_asset_resp(asset)


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
            resp = await treedb.get_items_from_related_id(related_id=asset_id, headers=ctx.headers())
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


@router.put("/{asset_id}/access/{group_id}",
            response_model=ExposingGroup,
            summary="get asset")
async def put_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        body: AccessPolicyBody,
        configuration: Configuration = Depends(get_configuration)
):
    response = Optional[ExposingGroup]
    async with Context.start_ep(
            action='create access policy',
            request=request,
            response=lambda: response,
            with_attributes={"asset_id": asset_id}
    ) as ctx:
        assets_client = configuration.assets_client
        await assets_client.put_access_policy(asset_id=asset_id, group_id=group_id, body=body.dict(),
                                              headers=ctx.headers())
        policy = await assets_client.get_access_policy(asset_id=asset_id, group_id=group_id, headers=ctx.headers())
        response = ExposingGroup(name=to_group_scope(group_id), groupId=group_id, access=format_policy(policy))
        return response


@router.get("/{asset_id}/statistics",
            summary="get asset")
async def statistics(
        request: Request,
        asset_id: str,
        bins_count: int = Query(25, alias="bins-count"),
        configuration: Configuration = Depends(get_configuration)
):
    headers = generate_headers_downstream(request.headers)
    assets_client = configuration.assets_client
    resp = await assets_client.query_latest_access(asset_id=asset_id, max_count=1000, headers=headers)
    if not resp['records']:
        return {
            "accessHistory": {
                "bins": [],
                "binSize": 0,
            }
        }
    timestamps = [datetime.fromtimestamp(r['timestamp']).timestamp() for r in resp['records']]
    start, end = min(timestamps), datetime.now().timestamp()
    r = []
    bin_size = (end - start) / bins_count
    indexes = [(t - start) / bin_size for t in timestamps]
    for k, g in itertools.groupby(indexes, key=lambda index: int(index)):
        date = datetime.fromtimestamp(start + k * bin_size)
        count = len(list(g))
        r.append({"date": date, "count": count})

    return {
        "accessHistory": {
            "bins": r,
            "binSize": bin_size,
        }
    }
