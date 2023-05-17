# standard library
from dataclasses import dataclass, field

# typing
from typing import Dict

# third parties
import aiohttp

# Youwol utilities
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class AccountsClient:
    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    async def healthz(self, **kwargs):
        url = f"{self.url_base}/healthz"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    drives = await resp.json()
                    return drives

                await raise_exception_from_response(resp, **kwargs)

    async def get_session_details(self, **kwargs):
        url = f"{self.url_base}/session"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp
                await raise_exception_from_response(resp, **kwargs)
