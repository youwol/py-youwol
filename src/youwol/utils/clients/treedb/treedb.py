# standard library
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader


@dataclass(frozen=True)
class TreeDbClient:
    """
    HTTP client of the [tree_db](@yw-nav-mod:youwol.backends.tree_db) service.
    """

    url_base: str
    """
    Base URL used for the request.
    """
    request_executor: RequestExecutor
    """
    Request executor.
    """

    async def healthz(self, headers: dict[str, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_drives(self, group_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.list_drives'>
        tree_db.list_drives</a>.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/groups/{group_id}/drives",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_drive(self, drive_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_drive'>
        tree_db.get_drive</a>.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/drives/{drive_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_default_drive(self, group_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_default_drive'>
        tree_db.get_default_drive</a>.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/groups/{group_id}/default-drive",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_default_user_drive(self, headers: dict[str, str], **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_default_user_drive'>
        tree_db.get_default_user_drive</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.create_drive'>
        tree_db.create_drive</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.update_drive'>
        tree_db.update_drive</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.delete_drive'>
        tree_db.delete_drive</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.create_folder'>
        tree_db.create_folder</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.update_folder'>
        tree_db.update_folder</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.move'>
        tree_db.move</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.borrow'>
        tree_db.borrow</a>.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.queue_delete_folder'>
        tree_db.queue_delete_folder</a>.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/folders/{folder_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def remove_item(self, item_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.queue_delete_item'>
        tree_db.queue_delete_item</a>.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_item(self, item_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_item'>
        tree_db.get_item</a>.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/items/{item_id}",
            default_reader=json_reader,
            headers=headers,
            **kwargs,
        )

    async def get_path(self, item_id, headers: dict[str, str], **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_path'>
        tree_db.get_path</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_path_folder'>
        tree_db.get_path_folder</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_entity'>
        tree_db.get_entity</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_items_by_asset_id'>
        tree_db.get_items_by_asset_id</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.update_item'>
        tree_db.update_item</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_folder'>
        tree_db.get_folder</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.get_children'>
        tree_db.get_children</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.list_deleted'>
        tree_db.list_deleted</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.purge_drive'>
        tree_db.purge_drive</a>.
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
        <a href='@yw-nav-func:youwol.backends.tree_db.root_paths.create_item'>
        tree_db.create_item</a>.
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
