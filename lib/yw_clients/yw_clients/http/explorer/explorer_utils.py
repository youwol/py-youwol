# Youwol clients
from yw_clients.http.explorer import ExplorerClient, FolderBody, NewDriveBody


async def ensure_pathname(
    group_id: str,
    drive_name: str,
    folders_name: list[str],
    treedb_client: ExplorerClient,
    headers: dict[str, str],
):
    resp_drives = await treedb_client.get_drives(group_id=group_id, headers=headers)
    drive = next((d for d in resp_drives.drives if d.name == drive_name), None)
    if not drive:
        drive = await treedb_client.create_drive(
            group_id=group_id, body=NewDriveBody(name=drive_name), headers=headers
        )

    parent_folder_id = drive.driveId

    for folder_name in folders_name:
        resp_children = await treedb_client.get_children(
            folder_id=parent_folder_id, headers=headers
        )
        folder = next((d for d in resp_children.folders if d.name == folder_name), None)
        if not folder:
            folder = await treedb_client.create_folder(
                parent_folder_id=parent_folder_id,
                body=FolderBody(name=folder_name),
                headers=headers,
            )
        parent_folder_id = folder.folderId

    return parent_folder_id
