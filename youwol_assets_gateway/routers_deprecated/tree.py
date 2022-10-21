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
from youwol_assets_gateway.routers_deprecated.assets import get_asset_by_tree_id

router = APIRouter(tags=["assets-gateway.tree"])


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


@router.get("/default-drive",
            response_model=DefaultDriveResponse, summary="get user's default drive")
async def get_default_user_drive(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
):
    user = user_info(request)
    return await get_default_drive(request=request, group_id=private_group_id(user), configuration=configuration)


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
