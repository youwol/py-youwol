from enum import Enum

from fastapi import HTTPException

from youwol.backends.treedb.models import PathResponse, DriveResponse
from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import Context
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


class Label(Enum):
    BASH = "BASH"
    DELETE = "DELETE"
    RUNNING = "RUNNING"
    PACKAGE_DOWNLOADING = "PACKAGE_DOWNLOADING"
    RUN_PIPELINE_STEP = "RUN_PIPELINE_STEP"
    PIPELINE_STEP_STATUS_PENDING = "PIPELINE_STEP_STATUS_PENDING"
    PIPELINE_STEP_RUNNING = "PIPELINE_STEP_RUNNING"


async def ensure_path(path_item: PathResponse, assets_gateway_client: AssetsGatewayClient):

    folders = path_item.folders
    try:
        if folders:
            await assets_gateway_client.get_tree_folder(folder_id=folders[-1].folderId)
        else:
            await assets_gateway_client.get_tree_drive(drive_id=path_item.drive.driveId)
    except HTTPException as e:
        if e.status_code == 404:
            if len(folders) <= 1:
                await ensure_drive(path_item.drive, assets_gateway_client)
            else:
                await ensure_path(PathResponse(drive=path_item.drive, folders=folders[0:-1], item=path_item.item),
                                  assets_gateway_client)
            if not folders:
                return
            folder = folders[-1]
            body = {"folderId":  folder.folderId, "name": folder.name}
            await assets_gateway_client.create_folder(parent_folder_id=folder.parentFolderId, body=body)


async def ensure_drive(drive: DriveResponse,  assets_gateway_client: AssetsGatewayClient):

    try:
        await assets_gateway_client.get_tree_drive(drive_id=drive.driveId)
    except HTTPException as e:
        if e.status_code == 404:
            body = {"driveId": drive.driveId, "name": drive.name}
            await assets_gateway_client.create_drive(group_id=drive.groupId, body=body)
            return
        raise e


async def local_path(tree_item: dict, context: Context):

    treedb = LocalClients.get_treedb_client(context)
    return await treedb.get_path(item_id=tree_item['treeId'])


async def remote_path(tree_item: dict, context: Context):

    treedb = await RemoteClients.get_treedb_client(context)
    return await treedb.get_path(item_id=tree_item['treeId'])
