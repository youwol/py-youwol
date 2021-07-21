from typing import Any, List

from youwol.configuration import parse_json
from youwol.routers.upload.models import PathResp, Folder, Drive
from youwol_utils import to_group_scope
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from fastapi import HTTPException


async def ensure_path(path_item: PathResp, assets_gateway_client: AssetsGatewayClient):

    folders = path_item.folders
    try:
        if folders:
            await assets_gateway_client.get_tree_folder(folder_id=folders[0].folderId)
        else:
            await assets_gateway_client.get_tree_drive(drive_id=path_item.drive.driveId)
    except HTTPException as e:
        if e.status_code == 404:
            if len(folders) <= 1:
                await ensure_drive(path_item.drive, assets_gateway_client)
            else:
                await ensure_path(PathResp(drive=path_item.drive, group=path_item.group, folders=folders[1:]),
                                  assets_gateway_client)
            if not folders:
                return
            folder = folders[0]
            body = {"folderId":  folder.folderId, "name": folder.name}
            await assets_gateway_client.create_folder(parent_folder_id=folder.parentFolderId, body=body)


async def ensure_drive(drive: Drive,  assets_gateway_client: AssetsGatewayClient):

    try:
        await assets_gateway_client.get_tree_drive(drive_id=drive.driveId)
    except HTTPException as e:
        if e.status_code == 404:
            body = {"driveId": drive.driveId, "name": drive.name}
            await assets_gateway_client.create_drive(group_id=drive.groupId, body=body)
            return
        raise e


def local_path(tree_id: str, config):
    local_docdb = config.pathsBook.local_docdb
    items_treedb = parse_json(local_docdb / "tree_db" / "items" / "data.json")
    items_treedb = items_treedb['documents']
    folders_treedb = parse_json(local_docdb / "tree_db" / "folders" / "data.json")
    folders_treedb = folders_treedb['documents']
    drives_treedb = parse_json(local_docdb / "tree_db" / "drives" / "data.json")
    drives_treedb = drives_treedb['documents']

    tree_item = next(item for item in items_treedb if item['item_id'] == tree_id)
    tree_drive = next(item for item in drives_treedb if item['drive_id'] == tree_item['drive_id'])

    def path_rec(parent_folder_id) -> List[Folder]:
        folder = next((item for item in folders_treedb if item['folder_id'] == parent_folder_id), None)
        if not folder:
            return []
        return [Folder(name=folder['name'], folderId=folder['folder_id'], parentFolderId=folder['parent_folder_id'])]\
            + path_rec(folder['parent_folder_id'])

    return PathResp(
        group=to_group_scope(tree_item['group_id']),
        drive=Drive(name=tree_drive['name'], driveId=tree_drive['drive_id'], groupId=tree_drive['group_id']),
        folders=path_rec(tree_item['folder_id'])
        )


