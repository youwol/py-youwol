# standard library
from dataclasses import dataclass

# Youwol clients
from yw_clients.http.assets import AssetsClient
from yw_clients.http.cdn import CdnClient
from yw_clients.http.explorer import ExplorerClient
from yw_clients.http.files import FilesClient
from yw_clients.http.request_executor import RequestExecutor


@dataclass(frozen=True)
class AssetsGatewayClient:
    """
    HTTP client of the :mod:`assets_gateway <youwol.backends.assets_gateway>` service.

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

    def get_treedb_backend_router(self) -> ExplorerClient:
        """
        Return the proxied `TreeDbClient`.

        Return:
            The HTTP client
        """
        return ExplorerClient(
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
