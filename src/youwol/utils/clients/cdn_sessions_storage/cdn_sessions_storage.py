# standard library
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader
from youwol.utils.types import JSON


@dataclass(frozen=True)
class CdnSessionsStorageClient:
    """
    HTTP client of the :mod:`cdn_sessions_storage <youwol.backends.cdn_sessions_storage>` service.
    """

    url_base: str
    """
    Base URL used for the request.
    """
    request_executor: RequestExecutor
    """
    Request executor.
    """

    def base_path(self, package: str, key: str):
        return f"{self.url_base}/applications/{package}/{key}"

    async def get(self, package: str, key: str, **kwargs):
        """
        See description in cdn_sessions_storage
        :func:`get_data_no_namespace <youwol.backends.cdn_sessions_storage.root_paths.get_data_no_namespace>`
        """
        return await self.request_executor.get(
            url=self.base_path(package, key),
            default_reader=json_reader,
            **kwargs,
        )

    async def post(self, package: str, key: str, body: JSON, **kwargs):
        """
        See description in cdn_sessions_storage
        :func:`post_data_no_namespace <youwol.backends.cdn_sessions_storage.root_paths.post_data_no_namespace>`
        """
        return await self.request_executor.post(
            url=self.base_path(package, key),
            default_reader=json_reader,
            json=body,
            **kwargs,
        )
