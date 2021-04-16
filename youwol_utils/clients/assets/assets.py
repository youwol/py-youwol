from typing import Dict
import aiohttp
from dataclasses import dataclass, field
from aiohttp import FormData

from youwol_utils.clients.utils import raise_exception_from_response


@dataclass(frozen=True)
class AssetsClient:

    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    async def create_asset(self, body, **kwargs):

        url = f"{self.url_base}/assets"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def update_asset(self, asset_id: str, body, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def put_access_policy(self, asset_id: str, group_id: str, body, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/access/{group_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def post_image(self, asset_id: str, filename: str, src: bytes, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/images/{filename}"
        form_data = FormData()
        form_data.add_field('file', src, filename=filename, content_type='application/octet-stream')

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, data=form_data, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def remove_image(self, asset_id: str, filename: str, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/images/{filename}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def query(self, body, **kwargs):

        url = f"{self.url_base}/query"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get(self, asset_id: str, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def delete_asset(self, asset_id: str, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_access_policy(self, asset_id: str, group_id: str, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/access/{group_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_permissions(self, asset_id: str, **kwargs):

        url = f"{self.url_base}/assets/{asset_id}/permissions"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_records(self, body, **kwargs):

        url = f"{self.url_base}/records"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def record_access(self, raw_id: str, **kwargs):

        url = f"{self.url_base}/raw/access/{raw_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def query_latest_access(self, asset_id: str, max_count=100, **kwargs):

        url = f"{self.url_base}/raw/access/{asset_id}/query-latest"
        params = {"max-count":max_count}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, params=params, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)
