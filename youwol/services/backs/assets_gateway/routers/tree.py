import asyncio
import itertools
import json

from fastapi import APIRouter, UploadFile, File, Depends
from starlette.requests import Request

from ..configurations import Configuration, get_configuration
from youwol_utils import (generate_headers_downstream, is_authorized_write, HTTPException)
from ..models import (
    DrivesResponse, ChildrenResponse, DriveBody, DriveResponse,
    FolderResponse, FolderBody, DeletedResponse, MoveBody, ItemResponse, BorrowBody, PermissionsResponse, PutFolderBody,
    PutDriveBody,
    )
from ..package_drive import (pack_drive, unpack_drive, MockFile)
from ..routers.assets import get_asset_by_tree_id
from ..utils import to_item_resp, regroup_asset, to_folder_resp

router = APIRouter()


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


@router.put("/groups/{group_id}/drives", response_model=DriveResponse, summary="create a new drive")
async def create_drive(
        request: Request,
        group_id: str,
        drive: PutDriveBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    body = {
        'driveId': drive.driveId,
        'name': drive.name
        }
    resp = await treedb.create_drive(group_id=group_id, body=body, headers=headers)
    return DriveResponse(**resp)


@router.post("/drives/{drive_id}", response_model=DriveResponse, summary="create a new folder")
async def update_drive(
        request: Request,
        drive_id: str,
        drive: DriveBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    body = {'name': drive.name}
    resp = await treedb.update_drive(drive_id=drive_id, body=body, headers=headers)
    return DriveResponse(**resp)


@router.get("/drives/{drive_id}", response_model=DriveResponse, summary="get a drive")
async def get_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    resp = await treedb.get_drive(drive_id=drive_id, headers=headers)
    return DriveResponse(**resp)


@router.delete("/drives/{drive_id}", summary="remove a drive")
async def delete_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    await treedb.delete_drive(drive_id=drive_id, headers=headers)
    return {}


@router.get("/folders/{folder_id}/children", response_model=ChildrenResponse,
            summary="list drives of a group")
async def get_children(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    items_resp = await treedb.get_children(folder_id=folder_id, headers=headers)

    items = [to_item_resp(item) for item in items_resp['items']]
    folders = [FolderResponse(**folder) for folder in items_resp['folders']]
    return ChildrenResponse(items=items, folders=folders)


@router.get("/items/{item_id}", response_model=ItemResponse,
            summary="retrieve an item")
async def get_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    resp = await treedb.get_item(item_id=item_id, headers=headers)

    return to_item_resp(resp)


@router.get("/folders/{folder_id}", response_model=FolderResponse,
            summary="retrieve a folder")
async def get_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    resp = await treedb.get_folder(folder_id=folder_id, headers=headers)

    return to_folder_resp(resp)


@router.put("/folders/{parent_folder_id}", response_model=FolderResponse,
            summary="create a new folder")
async def create_folder(
        request: Request,
        parent_folder_id: str,
        folder: PutFolderBody,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    body = {
        'folderId': folder.folderId,
        'name': folder.name,
        'parentFolderId': parent_folder_id
        }
    resp = await treedb.create_folder(parent_folder_id=parent_folder_id, body=body, headers=headers)
    return FolderResponse(**resp)


@router.delete("/folders/{folder_id}", summary="remove a folder")
async def remove_folder(
        request: Request,
        folder_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    await treedb.remove_folder(folder_id=folder_id, headers=headers)

    return {}


@router.delete("/items/{item_id}", summary="remove an item")
async def remove_item(
        request: Request,
        item_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    await treedb.remove_item(item_id=item_id, headers=headers)
    return {}


@router.post("/folders/{folder_id}", response_model=FolderResponse,
             summary="create a new folder")
async def update_folder(
        request: Request,
        folder_id: str,
        folder: FolderBody,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    body = {'name': folder.name}
    resp = await treedb.update_folder(folder_id=folder_id, body=body, headers=headers)
    return FolderResponse(**resp)


@router.post("/{tree_id}/move", summary="move item")
async def move(
        request: Request,
        tree_id: str,
        body: MoveBody,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
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

    headers = generate_headers_downstream(request.headers)
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
    tree_item['itemId'] = None
    tree_item['metadata'] = json.dumps(metadata)
    post_resp = await tree_db.create_item(folder_id=body.destinationFolderId, body=tree_item, headers=headers)
    item = ItemResponse(treeId=post_resp['itemId'], folderId=post_resp['folderId'], rawId=asset.rawId,
                        assetId=asset.assetId, groupId=entity['entity']['groupId'], name=asset.name, kind=asset.kind,
                        borrowed=True)
    return item


@router.get("/{tree_id}/permissions",
            response_model=PermissionsResponse,
            summary="get the permissions on the asset")
async def permissions(
        request: Request,
        tree_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    tree_db, assets_db = configuration.treedb_client, configuration.assets_client

    tree_entity = await tree_db.get_entity(entity_id=tree_id, headers=headers)

    if tree_entity['entityType'] == 'folder':
        folder = tree_entity['entity']
        write = is_authorized_write(request, folder['groupId'])
        return PermissionsResponse(write=write, read=True, expiration=None, share=False)

    if tree_entity['entityType'] == 'drive':
        drive = tree_entity['entity']
        write = is_authorized_write(request, drive['groupId'])
        return PermissionsResponse(write=write, read=True, expiration=None, share=False)

    if tree_entity['entityType'] == 'item':
        item = tree_entity['entity']
        asset = await get_asset_by_tree_id(request=request, tree_id=tree_id, configuration=configuration)
        permission = await assets_db.get_permissions(asset_id=asset.assetId, headers=headers)
        metadata = json.loads(item['metadata'])
        if metadata['borrowed']:
            return PermissionsResponse(read=permission['read'], write=permission['write'], share=permission['share'],
                                       expiration=permission['expiration'])

        return PermissionsResponse(write=permission['write'], read=permission['read'], share=permission['share'],
                                   expiration=permission['expiration'])

    return PermissionsResponse(write=False, read=False, expiration=None, share=None)


@router.get("/drives/{drive_id}/deleted", response_model=DeletedResponse,
            summary="create a new folder")
async def get_deleted(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)):

    headers = generate_headers_downstream(request.headers)
    treedb = configuration.treedb_client
    resp = await treedb.get_deleted(drive_id=drive_id, headers=headers)
    return DeletedResponse(**resp)


@router.delete("/drives/{drive_id}/purge",
               summary="purge queued deletion of given drive")
async def purge(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
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


@router.put("/drives/{drive_id}/package",
            summary="package drive in one zip-file")
async def package(
        request: Request,
        drive_id: str,
        configuration: Configuration = Depends(get_configuration)):

    return await pack_drive(request=request, drive_id=drive_id, configuration=configuration)


@router.put("/drives/{drive_id}/unpack",
            summary="package drive in one zip-file")
async def unpack(
        request: Request,
        drive_id: str,
        file: UploadFile = File(...),
        configuration: Configuration = Depends(get_configuration)):

    return await unpack_drive(request=request, drive_id=drive_id, file=file, configuration=configuration)


@router.put("/items/{tree_id}/unpack",
            summary="unpack a drive-pack at current location")
async def unpack(
        request: Request,
        tree_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    asset, tree_item = await asyncio.gather(
        get_asset_by_tree_id(request=request, tree_id=tree_id),
        configuration.treedb_client.get_item(item_id=tree_id, headers=headers)
        )

    assets_stores = configuration.assets_stores()
    # asset.kind should be 'drive-pack' & should be used instead of hard coded value
    raw_store = next(store for store in assets_stores if store.path_name == "drive-pack")
    data = await raw_store.get_asset(request=request, raw_id=asset.rawId, rest_of_path="", headers=headers)

    return await unpack_drive(request=request, drive_id=tree_item['folderId'], file=MockFile("", asset.name, data.body),
                              configuration=configuration)
