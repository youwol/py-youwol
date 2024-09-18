# standard library
from base64 import b64encode

# third parties
import pytest
import requests

# Youwol clients
from yw_clients import AioHttpExecutor, EmptyResponse, YouwolHeaders
from yw_clients.http.assets_gateway import AssetsGatewayClient
from yw_clients.http.exceptions import UpstreamResponseException
from yw_clients.http.explorer import (
    BorrowBody,
    ChildrenResponse,
    DefaultDriveResponse,
    DriveResponse,
    DrivesResponse,
    EntityResponse,
    FolderBody,
    FolderResponse,
    ItemBody,
    ItemResponse,
    ItemsResponse,
    MoveEntityBody,
    MoveResponse,
    NewDriveBody,
    PathResponse,
    PurgeResponse,
    RenameBody,
)

headers = {YouwolHeaders.py_youwol_local_only: "true"}


@pytest.mark.asyncio
class TestExplorerClient:
    explorer = AssetsGatewayClient(
        url_base="http://localhost:2001/api/assets-gateway",
        request_executor=AioHttpExecutor(),
    ).explorer()

    async def test_api(self) -> None:
        requests.post(
            url="http://localhost:2001/admin/custom-commands/reset", json={}, timeout=10
        )
        default_drive = await self.explorer.get_default_user_drive(headers=headers)
        assert isinstance(default_drive, DefaultDriveResponse)
        default_drive_group = await self.explorer.get_default_drive(
            group_id=default_drive.groupId, headers=headers
        )
        assert isinstance(default_drive_group, DefaultDriveResponse)
        children = await self.explorer.get_children(
            folder_id=default_drive.homeFolderId, headers=headers
        )
        assert isinstance(children, ChildrenResponse)
        deleted = await self.explorer.get_deleted(
            drive_id=default_drive.driveId, headers=headers
        )
        assert isinstance(deleted, ChildrenResponse)
        purge = await self.explorer.purge_drive(
            drive_id=default_drive.driveId, headers=headers
        )
        assert isinstance(purge, PurgeResponse)
        item_body = ItemBody(
            name="test-pytest",
            kind="pytest",
            assetId=b64encode("test-asset-id".encode("utf-8")).decode(),
            borrowed=False,
        )
        item = await self.explorer.create_item(
            folder_id=default_drive.homeFolderId, body=item_body, headers=headers
        )
        assert isinstance(item, ItemResponse)
        item = await self.explorer.get_item(item_id=item.itemId, headers=headers)
        assert isinstance(item, ItemResponse)
        folder = await self.explorer.get_folder(
            folder_id=default_drive.homeFolderId, headers=headers
        )
        assert isinstance(folder, FolderResponse)
        updated = await self.explorer.update_item(
            item_id=item.itemId, body=RenameBody(name="renamed"), headers=headers
        )
        assert isinstance(updated, ItemResponse)
        items = await self.explorer.get_items_from_asset(
            asset_id=item.assetId, headers=headers
        )
        assert isinstance(items, ItemsResponse)
        entity = await self.explorer.get_entity(entity_id=item.itemId, headers=headers)
        assert isinstance(entity, EntityResponse)
        path_folder = await self.explorer.get_path_folder(
            folder_id=default_drive.homeFolderId, headers=headers
        )
        assert isinstance(path_folder, PathResponse)
        path_item = await self.explorer.get_path(item_id=item.itemId, headers=headers)
        assert isinstance(path_item, PathResponse)
        try:
            await self.explorer.borrow(
                item_id=item.itemId,
                body=BorrowBody(destinationFolderId=default_drive.systemFolderId),
                headers=headers,
            )
        except UpstreamResponseException:
            # It is not possible to borrow an item not related to an asset.
            pass
        empty_resp = await self.explorer.remove_item(
            item_id=item.itemId, headers=headers
        )
        assert isinstance(empty_resp, EmptyResponse)

        new_folder = await self.explorer.create_folder(
            parent_folder_id=default_drive.homeFolderId,
            body=FolderBody(name="test-folder"),
            headers=headers,
        )
        assert isinstance(new_folder, FolderResponse)
        updated_folder = await self.explorer.update_folder(
            folder_id=new_folder.folderId,
            body=RenameBody(name="test-folder-renamed"),
            headers=headers,
        )
        assert isinstance(updated_folder, FolderResponse)

        moved_folder = await self.explorer.move(
            body=MoveEntityBody(
                targetId=updated_folder.folderId,
                destinationFolderId=default_drive.systemFolderId,
            ),
            headers=headers,
        )

        assert isinstance(moved_folder, MoveResponse)
        empty_resp = await self.explorer.remove_folder(
            folder_id=new_folder.folderId, headers=headers
        )
        assert isinstance(empty_resp, EmptyResponse)

        drive = await self.explorer.create_drive(
            group_id=default_drive.groupId,
            body=NewDriveBody(name="test-drive"),
            headers=headers,
        )
        assert isinstance(drive, DriveResponse)
        drive = await self.explorer.get_drive(drive_id=drive.driveId, headers=headers)
        assert isinstance(drive, DriveResponse)
        drives = await self.explorer.get_drives(
            group_id=default_drive.groupId, headers=headers
        )
        assert isinstance(drives, DrivesResponse)
        drive = await self.explorer.update_drive(
            drive_id=drive.driveId, body=RenameBody(name="renamed"), headers=headers
        )
        assert isinstance(drive, DriveResponse)
        empty_resp = await self.explorer.delete_drive(
            drive_id=drive.driveId, headers=headers
        )
        assert isinstance(empty_resp, EmptyResponse)
