
from typing import Dict
import aiohttp
from dataclasses import dataclass, field

from youwol_utils.clients.utils import raise_exception_from_response
from youwol_utils.types import JSON


@dataclass(frozen=True)
class AuthClient:

    url_base: str
    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    @property
    def user_info_url(self):
        return f"{self.url_base}/realms/youwol/protocol/openid-connect/userinfo"

    async def get_userinfo(self, bearer_token: str, **kwargs) -> JSON:

        headers = {**self.headers, **{'Authorization': f"Bearer {bearer_token}"}}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with await session.post(url=self.user_info_url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, **kwargs)
