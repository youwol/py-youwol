import asyncio
import itertools
import json
from typing import Dict, Optional

from fastapi import APIRouter, Depends
from starlette.requests import Request

from youwol_utils import (
    generate_headers_downstream, is_authorized_write, HTTPException, user_info, YouWolException,
    private_group_id,
)
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import Context, Label
from ..configurations import Configuration, get_configuration
from ..models import (
    DrivesResponse, ChildrenResponse, DriveBody, DriveResponse,
    FolderResponse, FolderBody, DeletedResponse, MoveBody, ItemResponse, BorrowBody, PermissionsResponse, PutFolderBody,
    PutDriveBody, DefaultDriveResponse, ItemsResponse
)
from ..routers.assets import get_asset_by_tree_id
from ..utils import to_item_resp, regroup_asset, to_folder_resp

router = APIRouter()


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


async def ensure_items(
        folder_id: str,
        parent_folder_id: str,
        name: str,
        treedb: TreeDbClient,
        headers: Dict[str, str]
):
    try:
        await treedb.get_folder(folder_id=folder_id, headers=headers)
    except YouWolException as e:
        if e.status_code != 404:
            raise e
        return await treedb.create_folder(
            parent_folder_id=parent_folder_id,
            body={"name": name, "folderId": folder_id},
            headers=headers
        )


@router.get("/default-drive",
            response_model=DefaultDriveResponse, summary="get user's default drive")
async def get_default_user_drive(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
):
    user = user_info(request)
    return await get_default_drive(request=request, group_id=private_group_id(user), configuration=configuration)


@router.get("/groups/{group_id}/drives", response_model=DrivesResponse, summary="list drives of a group")
async def get_drives(
        request: Request,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    drives_resp = await treedb.get_drives(group_id=group_id, headers=headers)
    drives = [DriveResponse(**drive) for drive in drives_resp['drives']]
    return DrivesResponse(drives=drives)


@router.get("/groups/{group_id}/default-drive",
            response_model=DefaultDriveResponse, summary="get group's default drive")
async def get_default_drive(
        request: Request,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
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
            ctx.warning("Default drive does not exist yet, start creation")
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

        system_packages = await ensure_folder(name="Packages", folder_id=f"{default_drive_id}_system_package",
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


@router.put("/groups/{group_id}/drives", response_model=DriveResponse, summary="create a new drive")
async def create_drive(
        request: Request,
        group_id: str,
        drive: PutDriveBody,
        configuration: Configuration = Depends(get_configuration)
):
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


@router.post("/drives/{drive_id}", response_model=DriveResponse, summary="create a new folder")
async def update_drive(
        request: Request,
        drive_id: str,
        drive: DriveBody,
        configuration: Configuration = Depends(get_configuration)
):
    resp: Optional[DriveResponse] = None
    async with Context.start_ep(
            request=request,
            action="update drive",
            body=drive,
            response=lambda: resp,
            with_attributes={'drive_id': drive_id}
    ) as ctx:
        headers = ctx.headers()
        treedb = configuration.treedb_client
        body = {'name': drive.name}
        resp = DriveResponse(
            **await treedb.update_drive(drive_id=drive_id, body=body, headers=headers)
        )


@router.get("/drives/{drive_id}", response_model=DriveResponse, summary="get a drive")
async def get_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
):
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


@router.delete("/drives/{drive_id}", summary="remove a drive")
async def delete_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request,
            action="delete drive",
            with_attributes={'drive_id': drive_id}
    ) as ctx:
        treedb = configuration.treedb_client
        await treedb.delete_drive(drive_id=drive_id, headers=ctx.headers())
        return {}


@router.get("/folders/{folder_id}/children", response_model=ChildrenResponse,
            summary="list drives of a group")
async def get_children(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    response = Optional[ChildrenResponse]
    async with Context.start_ep(
            request=request,
            action="get children",
            response=lambda: response,
            with_attributes={'folder_id': folder_id}
    ) as ctx:
        headers = ctx.headers()
        treedb = configuration.treedb_client
        items_resp = await treedb.get_children(folder_id=folder_id, headers=headers)

        items = [to_item_resp(item) for item in items_resp['items']]
        folders = [FolderResponse(**folder) for folder in items_resp['folders']]
        response = ChildrenResponse(items=items, folders=folders)
        return response


@router.get("/items/{item_id}", response_model=ItemResponse,
            summary="retrieve an item")
async def get_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[ItemResponse]
    async with Context.start_ep(
            request=request,
            action="get item",
            response=lambda: response,
            with_attributes={'item_id': item_id}
    ) as ctx:
        treedb = configuration.treedb_client
        response = to_item_resp(
            await treedb.get_item(item_id=item_id, headers=ctx.headers())
        )
        return response


@router.get("/items/from-related/{related_id}",
            summary="get an item",
            response_model=ItemsResponse)
async def get_items_by_related_id(
        request: Request,
        related_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    response = Optional[ItemResponse]
    async with Context.start_ep(
            request=request,
            action="get item from related id",
            response=lambda: response,
            with_attributes={'related_id': related_id}
    ) as ctx:
        treedb = configuration.treedb_client
        resp = await treedb.get_items_from_related_id(related_id=related_id, headers=ctx.headers())
        response = ItemsResponse(items=[to_item_resp(item) for item in resp['items']])
        return response


@router.get("/folders/{folder_id}", response_model=FolderResponse,
            summary="retrieve a folder")
async def get_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[FolderResponse]
    async with Context.start_ep(
            request=request,
            action="get folder",
            response=lambda: response,
            with_attributes={'folder_id': folder_id}
    ) as ctx:
        treedb = configuration.treedb_client
        response = to_folder_resp(
            await treedb.get_folder(folder_id=folder_id, headers=ctx.headers())
        )
        return response


@router.put("/folders/{parent_folder_id}", response_model=FolderResponse,
            summary="create a new folder")
async def create_folder(
        request: Request,
        parent_folder_id: str,
        folder: PutFolderBody,
        configuration: Configuration = Depends(get_configuration)):
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


@router.delete("/folders/{folder_id}", summary="remove a folder")
async def remove_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request,
            action="remove folder",
            with_attributes={'folder_id': folder_id}
    ) as ctx:
        treedb = configuration.treedb_client
        await treedb.remove_folder(folder_id=folder_id, headers=ctx.headers())
        return {}


@router.delete("/items/{item_id}", summary="remove an item")
async def remove_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request,
            action="remove item",
            with_attributes={'item_id': item_id}
    ) as ctx:
        treedb = configuration.treedb_client
        await treedb.remove_item(item_id=item_id, headers=ctx.headers())
        return {}


@router.post("/folders/{folder_id}", response_model=FolderResponse,
             summary="update folder")
async def update_folder(
        request: Request,
        folder_id: str,
        folder: FolderBody,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[FolderResponse]
    async with Context.start_ep(
            request=request,
            action="update folder",
            response=lambda: response,
            with_attributes={'folder_id': folder_id}
    ) as ctx:
        treedb = configuration.treedb_client
        body = {'name': folder.name}
        resp = await treedb.update_folder(folder_id=folder_id, body=body, headers=ctx.headers())
        return FolderResponse(**resp)


@router.post("/{tree_id}/move", summary="move item")
async def move(
        request: Request,
        tree_id: str,
        body: MoveBody,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request,
            action="move folder or item",
            body=body,
            with_attributes={'tree_id': tree_id}
    ) as ctx:
        headers = ctx.headers()
        tree_db, assets_db, assets_stores = configuration.treedb_client, configuration.assets_client, \
                                            configuration.assets_stores()

        resp = await tree_db.get_entity(entity_id=tree_id, include_drives=False, headers=headers)
        group_id = resp['entity']['groupId']
        body_move_tree = {
            'targetId': tree_id,
            "destinationFolderId": body.destinationFolderId
        }
        moved = await tree_db.move(body=body_move_tree, headers=headers)

        async def regroup(tree_item):
            actual_asset = await get_asset_by_tree_id(request=request, tree_id=tree_item['itemId'],
                                                      configuration=configuration)
            return await regroup_asset(request=request, asset=actual_asset, tree_item=tree_item,
                                       configuration=configuration)

        assets_to_regroup = [m for m in moved['items'] if m['groupId'] != group_id]
        await asyncio.gather(*[regroup(tree_item) for tree_item in assets_to_regroup])

        return await get_children(request, folder_id=body.destinationFolderId, configuration=configuration)


@router.post("/{tree_id}/borrow",
             response_model=ItemResponse,
             summary="borrow item")
async def borrow(
        request: Request,
        tree_id: str,
        body: BorrowBody,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[ItemResponse]

    async with Context.start_ep(
            request=request,
            action="borrow folder or item",
            body=body,
            response=lambda: response,
            with_attributes={'tree_id': tree_id}
    ) as ctx:
        headers = ctx.headers()
        tree_db, assets_db, assets_stores = configuration.treedb_client, configuration.assets_client, \
                                            configuration.assets_stores()

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


@router.get("/{tree_id}/permissions",
            response_model=PermissionsResponse,
            summary="get the permissions on the asset")
async def permissions(
        request: Request,
        tree_id: str,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[PermissionsResponse]

    async with Context.start_ep(
            request=request,
            action="get permission",
            response=lambda: response,
            with_attributes={'tree_id': tree_id}
    ) as ctx:

        headers = ctx.headers()
        tree_db, assets_db = configuration.treedb_client, configuration.assets_client

        tree_entity = await tree_db.get_entity(entity_id=tree_id, headers=headers)

        if tree_entity['entityType'] == 'folder':
            folder = tree_entity['entity']
            write = is_authorized_write(request, folder['groupId'])
            response = PermissionsResponse(write=write, read=True, expiration=None, share=False)
            return response

        if tree_entity['entityType'] == 'drive':
            drive = tree_entity['entity']
            write = is_authorized_write(request, drive['groupId'])
            response = PermissionsResponse(write=write, read=True, expiration=None, share=False)
            return response

        if tree_entity['entityType'] == 'item':
            item = tree_entity['entity']
            asset = await get_asset_by_tree_id(request=request, tree_id=tree_id, configuration=configuration)
            permission = await assets_db.get_permissions(asset_id=asset.assetId, headers=headers)
            metadata = json.loads(item['metadata'])
            if metadata['borrowed']:
                response = PermissionsResponse(read=permission['read'], write=permission['write'],
                                               share=permission['share'], expiration=permission['expiration'])
                return response

            response = PermissionsResponse(write=permission['write'], read=permission['read'],
                                           share=permission['share'], expiration=permission['expiration'])
            return response

        response = PermissionsResponse(write=False, read=False, expiration=None, share=False)
        return response


@router.get("/drives/{drive_id}/deleted", response_model=DeletedResponse,
            summary="get deleted items")
async def get_deleted(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)):
    response = Optional[DeletedResponse]

    async with Context.start_ep(
            request=request,
            action="get deleted items",
            response=lambda: response,
            with_attributes={'tree_id': drive_id}
    ) as ctx:
        treedb = configuration.treedb_client
        response = DeletedResponse(
            **await treedb.get_deleted(drive_id=drive_id, headers=ctx.headers())
        )
        return response


@router.delete("/drives/{drive_id}/purge",
               summary="purge queued deletion of given drive")
async def purge(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request,
            action="purge",
            with_attributes={'drive_id': drive_id}
    ) as ctx:
        headers = ctx.headers()
        assets_db, treedb_client = configuration.assets_client, configuration.treedb_client
        assets_stores = configuration.assets_stores()

        tree_items = await treedb_client.purge_drive(drive_id=drive_id, headers=headers)

        async def get_asset(treedb_item):
            metadata = json.loads(treedb_item["metadata"])
            return await assets_db.get(asset_id=metadata['assetId'], headers=headers)

        def is_borrowed(item):
            metadata = json.loads(item["metadata"])
            return 'borrowed' in metadata and metadata['borrowed']

        coroutines = [get_asset(item) for item in tree_items['items'] if not is_borrowed(item)]
        all_assets = await asyncio.gather(*coroutines)

        await asyncio.gather(*[assets_db.delete_asset(asset_id=flux_asset["assetId"], headers=headers)
                               for flux_asset in all_assets])

        coroutines = []
        all_assets = sorted(all_assets, key=lambda asset: asset['kind'])
        for kind, group in itertools.groupby(all_assets, lambda asset: asset['kind']):
            store = next(store for store in assets_stores if store.path_name == kind)
            coroutines = coroutines + [store.delete_asset(request=request, raw_id=asset['relatedId'], headers=headers)
                                       for asset in group]

        await asyncio.gather(*coroutines)
        return tree_items
