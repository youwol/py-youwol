# standard library
from dataclasses import dataclass

# Youwol clients
from yw_clients.common.json_utils import JSON
from yw_clients.http.aiohttp_utils import AioHttpExecutor, EmptyResponse


@dataclass(frozen=True)
class CdnSessionsStorageClient:
    """
    HTTP client of the :mod:`cdn_sessions_storage <youwol.backends.cdn_sessions_storage>` service.
    """

    url_base: str
    """
    Base URL used for the request.
    """
    request_executor: AioHttpExecutor
    """
    Request executor.
    """

    def base_path(self, package: str, key: str):
        return f"{self.url_base}/applications/{package}/{key}"

    async def get(
        self, package: str, key: str, headers: dict[str, str], **kwargs
    ) -> JSON:
        """
        See description in cdn_sessions_storage
        :func:`get_data_no_namespace <youwol.backends.cdn_sessions_storage.root_paths.get_data_no_namespace>`
        """
        return await self.request_executor.get(
            url=self.base_path(package, key),
            reader=self.request_executor.json_reader,
            headers=headers,
            **kwargs,
        )

    async def post(
        self, package: str, key: str, body: JSON, headers: dict[str, str], **kwargs
    ) -> EmptyResponse:
        """
        See description in cdn_sessions_storage
        :func:`post_data_no_namespace <youwol.backends.cdn_sessions_storage.root_paths.post_data_no_namespace>`
        """
        return await self.request_executor.post(
            url=self.base_path(package, key),
            reader=self.request_executor.typed_reader(EmptyResponse),
            json=body,
            headers=headers,
            **kwargs,
        )
