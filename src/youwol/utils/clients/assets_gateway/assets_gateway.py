# standard library
from dataclasses import dataclass

# third parties
import aiohttp

# Youwol utilities
from youwol.utils.clients.assets.assets import AssetsClient
from youwol.utils.clients.cdn import CdnClient
from youwol.utils.clients.files import FilesClient
from youwol.utils.clients.flux.flux import FluxClient
from youwol.utils.clients.request_executor import RequestExecutor, json_reader
from youwol.utils.clients.stories.stories import StoriesClient
from youwol.utils.clients.treedb.treedb import TreeDbClient


@dataclass(frozen=True)
class AssetsGatewayClient:
    """
    HTTP client of the [assets_gateway](@yw-nav-mod:youwol.backends.assets_gateway) service.

    This client essentially provides clients for the proxied services by `assets_gateway`.
    """

    url_base: str
    """
    Base URL used for the request.
    """

    request_executor: RequestExecutor
    """
    Request executor.
    """

    @staticmethod
    def get_aiohttp_connector():
        return aiohttp.TCPConnector(verify_ssl=False)

    def get_assets_backend_router(self) -> AssetsClient:
        """
        Return the proxied `AssetsClient`.

        Return:
            The HTTP client
        """
        return AssetsClient(
            url_base=f"{self.url_base}/assets-backend",
            request_executor=self.request_executor,
        )

    def get_treedb_backend_router(self) -> TreeDbClient:
        """
        Return the proxied `TreeDbClient`.

        Return:
            The HTTP client
        """
        return TreeDbClient(
            url_base=f"{self.url_base}/treedb-backend",
            request_executor=self.request_executor,
        )

    def get_files_backend_router(self) -> FilesClient:
        """
        Return the proxied `FilesClient`.

        Return:
            The HTTP client
        """
        return FilesClient(
            url_base=f"{self.url_base}/files-backend",
            request_executor=self.request_executor,
        )

    def get_flux_backend_router(self) -> FluxClient:
        return FluxClient(
            url_base=f"{self.url_base}/flux-backend",
            request_executor=self.request_executor,
        )

    def get_stories_backend_router(self) -> StoriesClient:
        return StoriesClient(
            url_base=f"{self.url_base}/stories-backend",
            request_executor=self.request_executor,
        )

    def get_cdn_backend_router(self) -> CdnClient:
        """
        Return the proxied `CdnClient`.

        Return:
            The HTTP client
        """
        return CdnClient(
            url_base=f"{self.url_base}/cdn-backend",
            request_executor=self.request_executor,
        )

    async def healthz(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz",
            default_reader=json_reader,
            **kwargs,
        )
