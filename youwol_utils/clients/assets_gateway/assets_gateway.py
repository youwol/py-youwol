from dataclasses import dataclass, field
from typing import Dict, Any, Optional

import aiohttp

from youwol_utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class AssetsGatewayClient:

    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})

    @staticmethod
    def get_aiohttp_connector():
        return aiohttp.TCPConnector(verify_ssl=False)

    async def healthz(self, **kwargs):
        url = f"{self.url_base}/healthz"
        async with aiohttp.ClientSession(
                connector=self.get_aiohttp_connector(),
                headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def put_asset_with_raw(self, kind: str, folder_id: str, data: Any, rest_of_path="", group_id: str = None,
                                 **kwargs):

        url = f"{self.url_base}/assets/{kind}/location/{folder_id}{rest_of_path}"
        params = {"group-id": group_id} if group_id else {}
        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.put(url=url, data=data, params=params, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def update_raw_asset(self, kind: str, raw_id: str, data: Any, rest_of_path: Optional[str] = None, **kwargs):
        url = f"{self.url_base}/raw/{kind}/{raw_id}"
        if rest_of_path:
            url = url + f"/{rest_of_path}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.post(url=url, data=data, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_raw(self, kind: str, raw_id: str, content_type=None, **kwargs):

        url = f"{self.url_base}/raw/{kind}/{raw_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url,  **kwargs) as resp:
                if resp.status == 200:
                    if content_type == "application/json":
                        return await resp.json()
                    if content_type == "text/html":
                        return await resp.text()
                    return await resp.read()
                await raise_exception_from_response(resp)

    async def get_raw_metadata(self, kind: str, raw_id: str, rest_of_path: str = None, **kwargs):

        url = f"{self.url_base}/raw/{kind}/metadata/{raw_id}"
        url = url if not rest_of_path else f"{url}/{rest_of_path}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url,  **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_tree_item(self, item_id: str, **kwargs):

        url = f"{self.url_base}/tree/items/{item_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def delete_tree_item(self, item_id: str, **kwargs):

        url = f"{self.url_base}/tree/items/{item_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def delete_tree_folder(self, folder_id: str, **kwargs):

        url = f"{self.url_base}/tree/folders/{folder_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_tree_items_by_related_id(self, related_id: str, **kwargs):

        url = f"{self.url_base}/tree/items/from-related/{related_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_permissions(self, item_id: str, **kwargs):

        url = f"{self.url_base}/tree/{item_id}/permissions"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def move_tree_item(self, tree_id: str, body, **kwargs):

        url = f"{self.url_base}/tree/{tree_id}/move"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def borrow_tree_item(self, tree_id: str, body, **kwargs):

        url = f"{self.url_base}/tree/{tree_id}/borrow"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_tree_folder(self, folder_id: str, **kwargs):

        url = f"{self.url_base}/tree/folders/{folder_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_tree_folder_children(self, folder_id: str, **kwargs):

        url = f"{self.url_base}/tree/folders/{folder_id}/children"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def create_folder(self, parent_folder_id: str, body, **kwargs):

        url = f"{self.url_base}/tree/folders/{parent_folder_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.put(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_tree_drive(self, drive_id: str, **kwargs):

        url = f"{self.url_base}/tree/drives/{drive_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def create_drive(self, group_id: str, body, **kwargs):

        url = f"{self.url_base}/tree/groups/{group_id}/drives"
        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.put(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_default_user_drive(self, **kwargs):

        url = f"{self.url_base}/tree/default-drive"
        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def purge_drive(self, drive_id: str, **kwargs):

        url = f"{self.url_base}/tree/drives/{drive_id}/purge"
        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_groups(self, **kwargs):

        url = f"{self.url_base}/groups"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_drives(self, group_id: str,  **kwargs):

        url = f"{self.url_base}/tree/groups/{group_id}/drives"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url,  **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_asset_metadata(self, asset_id: str,  **kwargs):

        url = f"{self.url_base}/assets/{asset_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url,  **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def get_asset_access(self, asset_id: str, **kwargs):
        url = f"{self.url_base}/assets/{asset_id}/access"
        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url,  **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def put_asset_access(self, asset_id: str, group_id: str, body, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/access/{group_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.put(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def update_asset(self, asset_id: str, body, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def post_asset_image(self, asset_id: str, filename: str, data, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/images/{filename}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.post(url=url, data=data, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def remove_asset_image(self, asset_id: str, filename: str, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/images/{filename}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def cdn_delete_version(self, library_name: str, version: str, **kwargs):

        url = f"{self.url_base}/cdn/libraries/{library_name}/{version}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.delete(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def cdn_get_package(self, library_name: str, version: str, metadata=False, **kwargs):

        url = f"{self.url_base}/cdn/libraries/{library_name}/{version}"
        params = {"metadata": str(metadata)}

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url, params=params, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json() if metadata else await resp.read()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def cdn_get_versions(self, package_id: str, **kwargs):

        url = f"{self.url_base}/raw/package/metadata/{package_id}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def cdn_loading_graph(self, body, **kwargs):

        url = f"{self.url_base}/cdn-backend/queries/loading-graph"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.post(url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)
