from typing import Dict, Any
import aiohttp
from dataclasses import dataclass, field

from youwol_utils.clients.utils import raise_exception_from_response


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

    async def put_asset_with_raw(self, kind: str, folder_id: str, data: Any, group_id: str = None, **kwargs):

        # data = files = {'file': open(zip_path, 'rb')}
        url = f"{self.url_base}/assets/{kind}/location/{folder_id}"
        params = {"group-id": group_id} if group_id else {}
        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.put(url=url, data=data, params=params, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
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

    async def get_tree_folder(self, folder_id: str, **kwargs):

        url = f"{self.url_base}/tree/folders/{folder_id}"

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

    async def get_groups(self, **kwargs):

        url = f"{self.url_base}/groups"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url=url,  **kwargs) as resp:
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

    async def cdn_get_package(self, library_name: str, version: str, **kwargs):

        url = f"{self.url_base}/cdn/libraries/{library_name}/{version}"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.get(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.read()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def cdn_loading_graph(self, body, **kwargs):

        url = f"{self.url_base}/cdn/queries/loading-graph"

        async with aiohttp.ClientSession(connector=self.get_aiohttp_connector(), headers=self.headers) as session:
            async with await session.post(url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)
