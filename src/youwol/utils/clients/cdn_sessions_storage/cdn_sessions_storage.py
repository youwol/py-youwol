# standard library
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader
from youwol.utils.types import JSON


@dataclass(frozen=True)
class CdnSessionsStorageClient:
    """
    HTTP client of the [cdn_sessions_storage](@yw-nav-mod:youwol.backends.cdn_sessions_storage) service.
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
        See description in
        <a href='@yw-nav-func:youwol.backends.cdn_sessions_storage.root_paths.get_data_no_namespace'>
        cdn_sessions_storage.get_data_no_namespace</a>.
        """
        return await self.request_executor.get(
            url=self.base_path(package, key),
            default_reader=json_reader,
            **kwargs,
        )

    async def post(self, package: str, key: str, body: JSON, **kwargs):
        """
        See description in
        <a href='@yw-nav-func:youwol.backends.cdn_sessions_storage.root_paths.post_data_no_namespace'>
        cdn_sessions_storage.post_data_no_namespace</a>.
        """
        return await self.request_executor.post(
            url=self.base_path(package, key),
            default_reader=json_reader,
            json=body,
            **kwargs,
        )
