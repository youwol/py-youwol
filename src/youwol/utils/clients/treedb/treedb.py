# standard library
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader


@dataclass(frozen=True)
class TreeDbClient:
    """
    HTTP client of the :mod:`tree_db <youwol.backends.tree_db>` service.
    """

    url_base: str
    """
    Base URL used for the request.
    """
    request_executor: RequestExecutor
    """
    Request executor.
    """

    async def get_drives(self, group_id: str, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`list_drives <youwol.backends.tree_db.routers.groups.list_drives>`
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/groups/{group_id}/drives",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_drive(self, drive_id: str, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`get_drive <youwol.backends.tree_db.routers.drives.get_drive_details>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/drives/{drive_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_default_drive(self, group_id: str, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`get_default_drive <youwol.backends.tree_db.routers.groups.get_group_default_drive>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/groups/{group_id}/default-drive",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_default_user_drive(self, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`get_default_user_drive <youwol.backends.tree_db.routers.drives.get_default_user_drive>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/default-drive",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def create_drive(
        self, group_id: str, body, headers: dict[str, str], **kwargs
    ):
        """
        See description in tree_db
        :func:`create_drive <youwol.backends.tree_db.routers.groups.create_group_drive>`.
        """
        return await self.request_executor.put(
            url=f"{self.url_base}/groups/{group_id}/drives",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def update_drive(
        self, drive_id: str, body, headers: dict[str, str], **kwargs
    ):
        """
        See description in tree_db
        :func:`update_drive <youwol.backends.tree_db.routers.drives.update_drive>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/drives/{drive_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def delete_drive(self, drive_id: str, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`delete_drive <youwol.backends.tree_db.routers.drives.delete_drive>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/drives/{drive_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def create_folder(
        self, parent_folder_id: str, body, headers: dict[str, str], **kwargs
    ):
        """
        See description in tree_db
        :func:`create_folder <youwol.backends.tree_db.routers.folders.create_child_folder>`.
        """
        return await self.request_executor.put(
            url=f"{self.url_base}/folders/{parent_folder_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def update_folder(
        self, folder_id: str, body, headers: dict[str, str], **kwargs
    ):
        """
        See description in tree_db
        :func:`update_folder <youwol.backends.tree_db.routers.folders.update_folder>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/folders/{folder_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def move(self, body, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`move <youwol.backends.tree_db.routers.entities.move>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/move",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def borrow(self, item_id: str, body, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`borrow <youwol.backends.tree_db.routers.items.borrow>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/items/{item_id}/borrow",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def remove_folder(self, folder_id: str, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`queue_delete_folder <youwol.backends.tree_db.routers.folders.queue_delete_folder>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/folders/{folder_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def remove_item(self, item_id: str, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`queue_delete_item <youwol.backends.tree_db.routers.items.queue_delete_item>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_item(self, item_id: str, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`get_item <youwol.backends.tree_db.routers.items.get_item>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_path(self, item_id, headers: dict[str, str], **kwargs):
        """
        See description in tree_db
        :func:`get_path <youwol.backends.tree_db.routers.items.get_path>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/items/{item_id}/path",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_path_folder(self, folder_id, headers: dict[str, str], **kwargs):
        """
        See description in
        :func:`get_path_folder <youwol.backends.tree_db.routers.folders.get_path_folder>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/folders/{folder_id}/path",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_entity(
        self,
        entity_id: str,
        headers: dict[str, str],
        include_drives: bool = True,
        include_folders: bool = True,
        include_items: bool = True,
        **kwargs,
    ):
        """
        See description in
        :func:`get_entity <youwol.backends.tree_db.routers.entities.get_entity>`.
        """
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
        self, asset_id: str, headers: dict[str, str], **kwargs
    ):
        """
        See description in
        :func:`get_items_by_asset_id <youwol.backends.tree_db.routers.items.get_items_by_asset_id>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/items/from-asset/{asset_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def update_item(self, item_id: str, body, headers: dict[str, str], **kwargs):
        """
        See description in
        :func:`update_item <youwol.backends.tree_db.routers.items.update_item>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def get_folder(self, folder_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        :func:`get_folder_details <youwol.backends.tree_db.routers.folders.get_folder_details>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/folders/{folder_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_children(self, folder_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        :func:`get_children <youwol.backends.tree_db.routers.folders.children>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/folders/{folder_id}/children",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_deleted(self, drive_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        :func:`list_deleted <youwol.backends.tree_db.routers.items.list_items_deleted>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/drives/{drive_id}/deleted",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def purge_drive(self, drive_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        :func:`purge_drive <youwol.backends.tree_db.routers.drives.purge_drive>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/drives/{drive_id}/purge",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def create_item(
        self, folder_id: str, body, headers: dict[str, str], **kwargs
    ):
        """
        See description in
        :func:`create_item <youwol.backends.tree_db.routers.items.create_item>`.
        """
        return await self.request_executor.put(
            url=f"{self.url_base}/folders/{folder_id}/items",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )

    async def get_records(self, body, headers: dict[str, str], **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/records",
            default_reader=json_reader,
            json=body,
            headers=headers,
            **kwargs,
        )
