# standard library
from dataclasses import dataclass, field

# typing
from typing import Dict

# third parties
import aiohttp

# Youwol utilities
from youwol.utils import CdnClient
from youwol.utils.clients.assets.assets import AssetsClient
from youwol.utils.clients.files import FilesClient
from youwol.utils.clients.flux.flux import FluxClient
from youwol.utils.clients.stories.stories import StoriesClient
from youwol.utils.clients.treedb.treedb import TreeDbClient
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class AssetsGatewayClient:
    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})

    @staticmethod
    def get_aiohttp_connector():
        return aiohttp.TCPConnector(verify_ssl=False)

    def get_assets_backend_router(self) -> AssetsClient:
        return AssetsClient(
            url_base=f"{self.url_base}/assets-backend", headers=self.headers
        )

    def get_treedb_backend_router(self) -> TreeDbClient:
        return TreeDbClient(
            url_base=f"{self.url_base}/treedb-backend", headers=self.headers
        )

    def get_files_backend_router(self) -> FilesClient:
        return FilesClient(
            url_base=f"{self.url_base}/files-backend", headers=self.headers
        )

    def get_flux_backend_router(self) -> FluxClient:
        return FluxClient(
            url_base=f"{self.url_base}/flux-backend", headers=self.headers
        )

    def get_stories_backend_router(self) -> StoriesClient:
        return StoriesClient(
            url_base=f"{self.url_base}/stories-backend", headers=self.headers
        )

    def get_cdn_backend_router(self) -> CdnClient:
        return CdnClient(url_base=f"{self.url_base}/cdn-backend", headers=self.headers)

    async def healthz(self, **kwargs):
        url = f"{self.url_base}/healthz"
        async with aiohttp.ClientSession(
            connector=self.get_aiohttp_connector(), headers=self.headers
        ) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)
