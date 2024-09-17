# standard library
from dataclasses import dataclass

# Youwol clients
from yw_clients.http.assets import AssetsClient
from yw_clients.http.explorer import ExplorerClient
from yw_clients.http.files import FilesClient
from yw_clients.http.request_executor import RequestExecutor
from yw_clients.http.webpm import WebpmClient


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

    def assets(self) -> AssetsClient:
        """
        Return the proxied `AssetsClient`.

        Return:
            The HTTP client
        """
        return AssetsClient(
            url_base=f"{self.url_base}/assets-backend",
            request_executor=self.request_executor,
        )

    def explorer(self) -> ExplorerClient:
        """
        Return the proxied `ExplorerClient`.

        Return:
            The HTTP client
        """
        return ExplorerClient(
            url_base=f"{self.url_base}/treedb-backend",
            request_executor=self.request_executor,
        )

    def files(self) -> FilesClient:
        """
        Return the proxied `FilesClient`.

        Return:
            The HTTP client
        """
        return FilesClient(
            url_base=f"{self.url_base}/files-backend",
            request_executor=self.request_executor,
        )

    def webpm(self) -> WebpmClient:
        """
        Return the proxied `WebpmClient`.

        Return:
            The HTTP client
        """
        return WebpmClient(
            url_base=f"{self.url_base}/cdn-backend",
            request_executor=self.request_executor,
        )
