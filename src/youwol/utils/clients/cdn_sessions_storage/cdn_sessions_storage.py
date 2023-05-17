# standard library
from dataclasses import dataclass, field

# typing
from typing import Dict

# third parties
import aiohttp

# Youwol utilities
from youwol.utils import JSON
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class CdnSessionsStorageClient:
    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})

    def base_path(self, package: str, key: str):
        return f"{self.url_base}/applications/{package}/{key}"

    async def get(self, package: str, key: str, **kwargs):
        url = self.base_path(package, key)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def post(self, package: str, key: str, body: JSON, **kwargs):
        url = self.base_path(package, key)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)
