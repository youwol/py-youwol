# standard library
from dataclasses import dataclass, field

# typing
from typing import Dict

# third parties
import aiohttp

# Youwol utilities
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class TreeDbClient:
    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    async def healthz(self, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/healthz"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def get_drives(self, group_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/groups/{group_id}/drives"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def get_drive(self, drive_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/drives/{drive_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def get_default_drive(self, group_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/groups/{group_id}/default-drive"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def get_default_user_drive(self, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/default-drive"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def create_drive(
        self, group_id: str, body, headers: Dict[str, str], **kwargs
    ):
        url = f"{self.url_base}/groups/{group_id}/drives"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def update_drive(
        self, drive_id: str, body, headers: Dict[str, str], **kwargs
    ):
        url = f"{self.url_base}/drives/{drive_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def delete_drive(self, drive_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/drives/{drive_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def create_folder(
        self, parent_folder_id: str, body, headers: Dict[str, str], **kwargs
    ):
        url = f"{self.url_base}/folders/{parent_folder_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    folder = await resp.json()
                    return folder

                await raise_exception_from_response(resp, **kwargs)

    async def update_folder(
        self, folder_id: str, body, headers: Dict[str, str], **kwargs
    ):
        url = f"{self.url_base}/folders/{folder_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    folder = await resp.json()
                    return folder

                await raise_exception_from_response(resp, **kwargs)

    async def move(self, body, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/move"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    folder = await resp.json()
                    return folder

                await raise_exception_from_response(resp, **kwargs)

    async def borrow(self, item_id: str, body, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/items/{item_id}/borrow"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    folder = await resp.json()
                    return folder

                await raise_exception_from_response(resp, **kwargs)

    async def remove_folder(self, folder_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/folders/{folder_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def remove_item(self, item_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/items/{item_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_item(self, item_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/items/{item_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def get_path(self, item_id, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/items/{item_id}/path"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def get_path_folder(self, folder_id, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/folders/{folder_id}/path"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def get_entity(
        self,
        entity_id: str,
        headers: Dict[str, str],
        include_drives: bool = True,
        include_folders: bool = True,
        include_items: bool = True,
        **kwargs,
    ):
        url = f"{self.url_base}/entities/{entity_id}"
        params = {
            "include-drives": int(include_drives),
            "include-folders": int(include_folders),
            "include-items": int(include_items),
        }
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(
                url=url, params=params, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def get_items_from_asset(
        self, asset_id: str, headers: Dict[str, str], **kwargs
    ):
        url = f"{self.url_base}/items/from-asset/{asset_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def update_item(self, item_id: str, body, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/items/{item_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def get_folder(self, folder_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/folders/{folder_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def get_children(self, folder_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/folders/{folder_id}/children"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def get_deleted(self, drive_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/drives/{drive_id}/deleted"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def purge_drive(self, drive_id: str, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/drives/{drive_id}/purge"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    return items

                await raise_exception_from_response(resp, **kwargs)

    async def create_item(
        self, folder_id: str, body, headers: Dict[str, str], **kwargs
    ):
        url = f"{self.url_base}/folders/{folder_id}/items"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    folder = await resp.json()
                    return folder

                await raise_exception_from_response(resp, **kwargs)

    async def get_records(self, body, headers: Dict[str, str], **kwargs):
        url = f"{self.url_base}/records"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=url, json=body, headers=headers, **kwargs
            ) as resp:
                if resp.status == 200:
                    folder = await resp.json()
                    return folder

                await raise_exception_from_response(resp, **kwargs)
