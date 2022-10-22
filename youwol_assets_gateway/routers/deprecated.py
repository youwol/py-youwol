from starlette.responses import Response

from youwol_assets_gateway.routers.common import assert_read_permissions_from_raw_id

from youwol_utils import to_group_scope, is_authorized_write
from youwol_utils.http_clients.assets_backend import PermissionsResp
from youwol_utils.http_clients.assets_gateway import (
    AssetResponse, OwnerInfo, ExposingGroup,
    ConsumerInfo, AccessInfo, OwningGroup, UpdateAssetBody
)
from youwol_assets_gateway.utils import to_asset_resp, format_policy
import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends
from starlette.requests import Request

from youwol_utils import (
    HTTPException, user_info, YouWolException, private_group_id,
)
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import Context, Label
from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.http_clients.assets_gateway import (
    DriveResponse, FolderResponse, ItemResponse, BorrowBody, PutFolderBody, PutDriveBody, DefaultDriveResponse
)

router = APIRouter(tags=["assets-gateway.deprecated"])


@router.get("/raw/{kind}/{raw_id}/{rest_of_path:path}",
            summary="get raw record DEPRECATED")
async def get_raw(
        request: Request,
        kind: str,
        rest_of_path: str,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    """
    This end point is deprecated, it is used in following circumstances (only related to cdn):
        - in @youwol/cdn-client/client.ts: the url constructed to fetch cdn files use:
         `/api/assets-gateway/raw/package/${cdn_url}`
         => it needs to be updated by `/api/assets-gateway/cdn-backend/resources/${cdn_url}`
         - in saved flux project and stories the above URL are 'pined' in a sort of '.lock' files
         => these project need to be updated after the first point is solved
    """
    async with Context.start_ep(
            request=request,
            with_attributes={"raw_id": raw_id, "path": rest_of_path}
    ) as ctx:
        if kind != "package":
            raise HTTPException(status_code=410, detail="Only 'package' kind is kept under get-raw.")
        version = rest_of_path.split('/')[0]
        rest_of_path = '/'.join(rest_of_path.split('/')[1:])
        await assert_read_permissions_from_raw_id(raw_id=raw_id, configuration=configuration, context=ctx)

        async def reader(resp_cdn):
            resp_bytes = await resp_cdn.read()
            return Response(content=resp_bytes, headers={k: v for k, v in resp_cdn.headers.items()})

        resp = await configuration.cdn_client.get_resource(
            library_id=raw_id,
            version=version,
            rest_of_path=rest_of_path,
            reader=reader,
            auto_decompress=False,
            headers=ctx.headers())

        return resp


@router.get("/assets/{asset_id}",
            response_model=AssetResponse,
            summary="get asset")
async def get(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in GET: routers/assets-backend/{asset_id}
    """

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


@router.get("/assets/location/{tree_id}",
            response_model=AssetResponse,
            summary="get an asset")
async def get_asset_by_tree_id(
        request: Request,
        tree_id: str,
        configuration: Configuration = Depends(get_configuration)):
    """
    Need to find out from where it is called in py-youwol.
    Not sure what to with, but it is only within py-youwol (not exposed by http-clients)
    """

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


@router.post("/assets/{asset_id}",
             response_model=AssetResponse,
             summary="get asset")
async def update_asset(
        request: Request,
        asset_id: str,
        body: UpdateAssetBody,
        configuration: Configuration = Depends(get_configuration)):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in POST: routers/assets-backend/{asset_id}
    """
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


@router.get("/assets/{asset_id}/access",
            response_model=AccessInfo,
            summary="get asset info w/ access")
async def access_info(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in GET: routers/assets-backend/{asset_id}/access-info
    """
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


async def ensure_folder(
        folder_id: str,
        parent_folder_id: str,
        name: str,
        treedb: TreeDbClient,
        context: Context
):
    async with context.start(
            action='ensure folder',
            with_attributes={"folder_id": folder_id, 'name': name}
    ) as ctx:
        try:
            resp = await treedb.get_folder(folder_id=folder_id, headers=ctx.headers())
            await ctx.info("Folder already exists")
            return resp
        except YouWolException as e:
            if e.status_code != 404:
                raise e
            await ctx.warning("Folder does not exist yet, start creation")
            return await treedb.create_folder(
                parent_folder_id=parent_folder_id,
                body={"name": name, "folderId": folder_id},
                headers=ctx.headers()
            )


@router.get("/tree/default-drive",
            response_model=DefaultDriveResponse, summary="get user's default drive")
async def get_default_user_drive(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in GET: routers/treedb-backend/groups/{group_id}/default-drive
    """
    user = user_info(request)
    return await get_default_drive(request=request, group_id=private_group_id(user), configuration=configuration)


@router.get("/tree/groups/{group_id}/default-drive",
            response_model=DefaultDriveResponse, summary="get group's default drive")
async def get_default_drive(
        request: Request,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in GET: routers/treedb-backend/groups/{group_id}/default-drive
    """
    async with Context.from_request(request=request).start(
            action="get default drive",
            with_labels=[Label.END_POINT],
            with_attributes={'group_id': group_id}
    ) as ctx:

        headers = ctx.headers()
        treedb = configuration.treedb_client
        default_drive_id = f"{group_id}_default-drive"
        try:
            await treedb.get_drive(drive_id=default_drive_id, headers=headers)
        except YouWolException as e:
            if e.status_code != 404:
                raise e
            await ctx.warning("Default drive does not exist yet, start creation")
            await treedb.create_drive(group_id=group_id,
                                      body={"name": "Default drive", "driveId": default_drive_id},
                                      headers=headers)

        download, home, system, desktop = await asyncio.gather(
            ensure_folder(name="Download", folder_id=f"{default_drive_id}_download",
                          parent_folder_id=default_drive_id, treedb=treedb, context=ctx),
            ensure_folder(name="Home", folder_id=f"{default_drive_id}_home", parent_folder_id=default_drive_id,
                          treedb=treedb, context=ctx),
            ensure_folder(name="System", folder_id=f"{default_drive_id}_system", parent_folder_id=default_drive_id,
                          treedb=treedb, context=ctx),
            ensure_folder(name="Desktop", folder_id=f"{default_drive_id}_desktop", parent_folder_id=default_drive_id,
                          treedb=treedb, context=ctx))

        system_packages = await ensure_folder(name="Packages", folder_id=f"{default_drive_id}_system_packages",
                                              parent_folder_id=system['folderId'], treedb=treedb, context=ctx)

        resp = DefaultDriveResponse(
            groupId=group_id,
            driveId=default_drive_id,
            driveName="Default drive",
            downloadFolderId=download['folderId'],
            downloadFolderName=download['name'],
            homeFolderId=home['folderId'],
            homeFolderName=home['name'],
            desktopFolderId=desktop['folderId'],
            desktopFolderName=desktop['name'],
            systemFolderId=system['folderId'],
            systemFolderName=system['name'],
            systemPackagesFolderId=system_packages['folderId'],
            systemPackagesFolderName=system_packages['name']
        )
        await ctx.info("Response", data=resp)
        return resp


@router.put("/tree/groups/{group_id}/drives", response_model=DriveResponse, summary="create a new drive")
async def create_drive(
        request: Request,
        group_id: str,
        drive: PutDriveBody,
        configuration: Configuration = Depends(get_configuration)
):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in PUT: routers/treedb-backend//groups/{group_id}/drives
    """
    resp: Optional[DriveResponse] = None
    async with Context.start_ep(
            request=request,
            action="create drive",
            body=drive,
            response=lambda: resp
    ) as ctx:
        headers = ctx.headers()
        treedb = configuration.treedb_client
        body = {
            'driveId': drive.driveId,
            'name': drive.name
        }
        resp = DriveResponse(
            **await treedb.create_drive(group_id=group_id, body=body, headers=headers)
        )
        return resp


@router.get("/tree/drives/{drive_id}", response_model=DriveResponse, summary="get a drive")
async def get_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in GET: routers/treedb-backend/drives/{drive_id}
    """
    resp: Optional[DriveResponse] = None
    async with Context.start_ep(
            request=request,
            action="get drive",
            response=lambda: resp,
            with_attributes={'drive_id': drive_id}
    ) as ctx:
        treedb = configuration.treedb_client
        resp = DriveResponse(
            **await treedb.get_drive(drive_id=drive_id, headers=ctx.headers())
        )
        return resp


@router.put("/tree/folders/{parent_folder_id}", response_model=FolderResponse,
            summary="create a new folder")
async def create_folder(
        request: Request,
        parent_folder_id: str,
        folder: PutFolderBody,
        configuration: Configuration = Depends(get_configuration)):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in PUT: routers/treedb-backend/folders/{folders_id}
    """
    response = Optional[FolderResponse]
    async with Context.start_ep(
            request=request,
            action="create folder",
            body=folder,
            response=lambda: response,
            with_attributes={'parent_folder_id': parent_folder_id}
    ) as ctx:
        treedb = configuration.treedb_client
        body = {
            'folderId': folder.folderId,
            'name': folder.name,
            'parentFolderId': parent_folder_id
        }
        response = FolderResponse(
            **await treedb.create_folder(parent_folder_id=parent_folder_id, body=body, headers=ctx.headers())
        )
        return response


@router.post("/tree/{tree_id}/borrow",
             response_model=ItemResponse,
             summary="borrow item")
async def borrow(
        request: Request,
        tree_id: str,
        body: BorrowBody,
        configuration: Configuration = Depends(get_configuration)):
    """
    Need to find out from where it is called in py-youwol.
    The same end-point is in PUT: routers/treedb-backend/items/{tree_id}/borrow
    """
    response = Optional[ItemResponse]

    async with Context.start_ep(
            request=request,
            action="borrow folder or item",
            body=body,
            response=lambda: response,
            with_attributes={'tree_id': tree_id}
    ) as ctx:
        headers = ctx.headers()
        tree_db, assets_db = configuration.treedb_client, configuration.assets_client

        tree_item, asset, entity = await asyncio.gather(
            tree_db.get_item(item_id=tree_id, headers=headers),
            get_asset_by_tree_id(request=request, configuration=configuration, tree_id=tree_id),
            tree_db.get_entity(entity_id=body.destinationFolderId, include_items=False, headers=headers)
        )

        permission = await assets_db.get_permissions(asset_id=asset.assetId, headers=headers)
        if not permission['share']:
            raise HTTPException(status_code=403, detail='The resource can not be shared')
        metadata = json.loads(tree_item['metadata'])
        metadata['borrowed'] = True
        tree_item['itemId'] = body.itemId
        tree_item['metadata'] = json.dumps(metadata)
        post_resp = await tree_db.create_item(folder_id=body.destinationFolderId, body=tree_item, headers=headers)
        response = ItemResponse(treeId=post_resp['itemId'], folderId=post_resp['folderId'],
                                driveId=post_resp['driveId'], rawId=asset.rawId, assetId=asset.assetId,
                                groupId=entity['entity']['groupId'], name=asset.name, kind=asset.kind, borrowed=True)
        return response
