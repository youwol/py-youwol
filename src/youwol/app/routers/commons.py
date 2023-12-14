# standard library
from enum import Enum

# third parties
from fastapi import HTTPException

# Youwol application
from youwol.app.environment import LocalClients, RemoteClients, YouwolEnvironment

# Youwol utilities
from youwol.utils import Context
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol.utils.http_clients.tree_db_backend import DriveResponse, PathResponse


class Label(Enum):
    BASH = "BASH"
    DELETE = "DELETE"
    RUNNING = "RUNNING"
    PACKAGE_DOWNLOADING = "PACKAGE_DOWNLOADING"
    RUN_PIPELINE_STEP = "RUN_PIPELINE_STEP"
    PIPELINE_STEP_STATUS_PENDING = "PIPELINE_STEP_STATUS_PENDING"
    PIPELINE_STEP_RUNNING = "PIPELINE_STEP_RUNNING"
    PROJECT_CREATING = "PROJECT_CREATING"


async def ensure_path(
    path_item: PathResponse,
    assets_gateway_client: AssetsGatewayClient,
    context: Context,
):
    async with context.start(action="ensure path") as ctx:
        await context.info(text="target path", data=path_item)
        folders = path_item.folders
        treedb_backend = assets_gateway_client.get_treedb_backend_router()
        try:
            if folders:
                await treedb_backend.get_folder(
                    folder_id=folders[-1].folderId, headers=ctx.headers()
                )
            else:
                await treedb_backend.get_drive(
                    drive_id=path_item.drive.driveId, headers=ctx.headers()
                )
        except HTTPException as e:
            if e.status_code == 404:
                if len(folders) <= 1:
                    await ensure_drive(
                        drive=path_item.drive,
                        assets_gateway_client=assets_gateway_client,
                        context=ctx,
                    )
                else:
                    path_item = PathResponse(
                        drive=path_item.drive,
                        folders=folders[0:-1],
                        item=path_item.item,
                    )
                    await ensure_path(
                        path_item=path_item,
                        assets_gateway_client=assets_gateway_client,
                        context=ctx,
                    )
                if not folders:
                    return
                folder = folders[-1]
                body = {"folderId": folder.folderId, "name": folder.name}
                await treedb_backend.create_folder(
                    parent_folder_id=folder.parentFolderId,
                    body=body,
                    headers=ctx.headers(),
                )


async def ensure_drive(
    drive: DriveResponse, assets_gateway_client: AssetsGatewayClient, context: Context
):
    async with context.start(action="ensure drive") as ctx:
        treedb_backend = assets_gateway_client.get_treedb_backend_router()
        try:
            await treedb_backend.get_drive(
                drive_id=drive.driveId, headers=ctx.headers()
            )
        except HTTPException as e:
            if e.status_code == 404:
                body = {"driveId": drive.driveId, "name": drive.name}
                await treedb_backend.create_drive(
                    group_id=drive.groupId, body=body, headers=ctx.headers()
                )
                return
            raise e


async def ensure_local_path(folder_id: str, env: YouwolEnvironment, context: Context):
    async with context.start(
        action="ensure_local_path", with_attributes={"folderId": folder_id}
    ) as ctx:
        local_gtw, local_treedb = LocalClients.get_assets_gateway_client(
            env=env
        ), LocalClients.get_treedb_client(env=env)
        try:
            await local_treedb.get_folder(folder_id=folder_id, headers=ctx.headers())
        except HTTPException as e:
            if e.status_code == 404:
                assets_gtw = await RemoteClients.get_twin_assets_gateway_client(env=env)
                remote_treedb = assets_gtw.get_treedb_backend_router()
                path = await remote_treedb.get_path_folder(
                    folder_id=folder_id, headers=context.headers()
                )
                path = PathResponse(**path)
                await ensure_path(
                    path_item=path, assets_gateway_client=local_gtw, context=context
                )


async def local_path(tree_item: dict, context: Context):
    env = await context.get("env", YouwolEnvironment)
    treedb = LocalClients.get_treedb_client(env=env)
    return await treedb.get_path(item_id=tree_item["treeId"], headers=context.headers())
