# standard library
from dataclasses import dataclass, field

# typing
from typing import Any, Awaitable, Callable, Dict

# third parties
import aiohttp

from aiohttp import ClientResponse

# Youwol utilities
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class FilesClient:
    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})

    async def healthz(self, **kwargs):
        url = f"{self.url_base}/healthz"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def upload(self, data, **kwargs):
        url = f"{self.url_base}/files"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, data=data, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def get_info(self, file_id: str, **kwargs):
        url = f"{self.url_base}/files/{file_id}/info"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def update_metadata(self, file_id: str, body, **kwargs):
        url = f"{self.url_base}/files/{file_id}/metadata"
        metadata = {k: v for k, v in body.items() if v}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=metadata, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def get(
        self,
        file_id: str,
        reader: Callable[[ClientResponse], Awaitable[Any]] = None,
        **kwargs,
    ):
        url = f"{self.url_base}/files/{file_id}"

        async with aiohttp.ClientSession(
            headers=self.headers, auto_decompress=False
        ) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    if reader:
                        return await reader(resp)
                    return await resp.read()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def remove(self, file_id: str, **kwargs):
        url = f"{self.url_base}/files/{file_id}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)
