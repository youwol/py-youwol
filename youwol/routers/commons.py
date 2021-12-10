from typing import List, Dict, Any

from pydantic import BaseModel

from configuration.clients import RemoteClients, LocalClients
from services.backs.treedb.models import PathResponse, DriveResponse
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from fastapi import HTTPException
from youwol.configuration.models_base import SkeletonParameter, Pipeline
from youwol.configuration.youwol_configuration import YouwolConfigurationFactory, yw_config
from youwol.context import Context

from youwol.routers.environment.router import status as env_status


class SkeletonResponse(BaseModel):
    name: str
    description: str
    parameters: List[SkeletonParameter]


class SkeletonsResponse(BaseModel):
    skeletons: List[SkeletonResponse]


class PostSkeletonBody(BaseModel):
    parameters: Dict[str, Any]


async def list_skeletons(
        pipelines: Dict[str, Pipeline]
        ):
    resp_skeletons = [
        SkeletonResponse(name=name, description=p.skeleton.description, parameters=p.skeleton.parameters)
        for name, p in pipelines.items() if p.skeleton
        ]

    return SkeletonsResponse(skeletons=resp_skeletons)


async def create_skeleton(
        body: PostSkeletonBody,
        pipeline: Pipeline,
        context: Context
        ):

    skeleton = pipeline.skeleton
    await skeleton.generate(pipeline.skeleton.folder, body.parameters, pipeline, context)
    await YouwolConfigurationFactory.reload()
    new_conf = await yw_config()
    await env_status(context.request, new_conf)
    return {}


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

"""
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

    folders = path_rec(tree_item['folder_id'])
    folders.reverse()
    return PathResp(
        group=to_group_scope(tree_item['group_id']),
        drive=Drive(name=tree_drive['name'], driveId=tree_drive['drive_id'], groupId=tree_drive['group_id']),
        folders=folders
        )
"""


async def local_path(tree_item: dict, context: Context):

    treedb = LocalClients.get_treedb_client(context)
    return await treedb.get_path(item_id=tree_item['treeId'])


async def remote_path(tree_item: dict, context: Context):

    treedb = await RemoteClients.get_treedb_client(context)
    return await treedb.get_path(item_id=tree_item['treeId'])
