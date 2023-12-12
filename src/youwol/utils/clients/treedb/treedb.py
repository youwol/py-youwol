# standard library
from dataclasses import dataclass

# typing
from typing import Dict

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader


@dataclass(frozen=True)
class TreeDbClient:
    url_base: str

    request_executor: RequestExecutor

    async def healthz(self, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_drives(self, group_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/groups/{group_id}/drives",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_drive(self, drive_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/drives/{drive_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_default_drive(self, group_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/groups/{group_id}/default-drive",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_default_user_drive(self, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/default-drive",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def create_drive(
        self, group_id: str, body, headers: Dict[str, str], **kwargs
    ):
        return await self.request_executor.put(
            url=f"{self.url_base}/groups/{group_id}/drives",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def update_drive(
        self, drive_id: str, body, headers: Dict[str, str], **kwargs
    ):
        return await self.request_executor.post(
            url=f"{self.url_base}/drives/{drive_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def delete_drive(self, drive_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/drives/{drive_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def create_folder(
        self, parent_folder_id: str, body, headers: Dict[str, str], **kwargs
    ):
        return await self.request_executor.put(
            url=f"{self.url_base}/folders/{parent_folder_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def update_folder(
        self, folder_id: str, body, headers: Dict[str, str], **kwargs
    ):
        return await self.request_executor.post(
            url=f"{self.url_base}/folders/{folder_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def move(self, body, headers: Dict[str, str], **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/move",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def borrow(self, item_id: str, body, headers: Dict[str, str], **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/items/{item_id}/borrow",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def remove_folder(self, folder_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/folders/{folder_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def remove_item(self, item_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_item(self, item_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_path(self, item_id, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/items/{item_id}/path",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_path_folder(self, folder_id, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/folders/{folder_id}/path",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_entity(
        self,
        entity_id: str,
        headers: Dict[str, str],
        include_drives: bool = True,
        include_folders: bool = True,
        include_items: bool = True,
        **kwargs,
    ):
        params = {
            "include-drives": int(include_drives),
            "include-folders": int(include_folders),
            "include-items": int(include_items),
        }
        return await self.request_executor.get(
            url=f"{self.url_base}/entities/{entity_id}",
            default_reader=json_reader,
            headers=headers,
            params=params,
            **kwargs,
        )

    async def get_items_from_asset(
        self, asset_id: str, headers: Dict[str, str], **kwargs
    ):
        return await self.request_executor.get(
            url=f"{self.url_base}/items/from-asset/{asset_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def update_item(self, item_id: str, body, headers: Dict[str, str], **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def get_folder(self, folder_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/folders/{folder_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_children(self, folder_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/folders/{folder_id}/children",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_deleted(self, drive_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/drives/{drive_id}/deleted",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def purge_drive(self, drive_id: str, headers: Dict[str, str], **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/drives/{drive_id}/purge",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def create_item(
        self, folder_id: str, body, headers: Dict[str, str], **kwargs
    ):
        return await self.request_executor.put(
            url=f"{self.url_base}/folders/{folder_id}/items",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def get_records(self, body, headers: Dict[str, str], **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/records",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )
