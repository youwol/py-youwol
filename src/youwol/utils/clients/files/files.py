# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Any, Callable, Optional

# third parties
from aiohttp import ClientResponse

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader
from youwol.utils.exceptions import upstream_exception_from_response


@dataclass(frozen=True)
class FilesClient:
    """
    HTTP client of the [files](@yw-nav-mod:youwol.backends.files) service.
    """

    url_base: str
    """
    Base URL used for the request.
    """

    request_executor: RequestExecutor
    """
    Request executor.
    """

    async def healthz(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz",
            default_reader=json_reader,
            **kwargs,
        )

    async def upload(self, data, **kwargs):
        """
        See description in
        [files.upload](@yw-nav-func:youwol.backends.files.root_paths.upload).
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/files",
            default_reader=json_reader,
            data=data,
            **kwargs,
        )

    async def get_info(self, file_id: str, **kwargs):
        """
        See description in
        [files.get_info](@yw-nav-func:youwol.backends.files.root_paths.get_info).
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/files/{file_id}/info",
            default_reader=json_reader,
            **kwargs,
        )

    async def update_metadata(self, file_id: str, body, **kwargs):
        """
        See description in
        [files.update_metadata](@yw-nav-func:youwol.backends.files.root_paths.update_metadata).
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/files/{file_id}/metadata",
            default_reader=json_reader,
            json={k: v for k, v in body.items() if v},
            **kwargs,
        )

    async def get(
        self,
        file_id: str,
        reader: Optional[Callable[[ClientResponse], Awaitable[Any]]] = None,
        **kwargs,
    ):
        """
        See description in
        [files.get_file](@yw-nav-func:youwol.backends.files.root_paths.get_file).
        """
        url = f"{self.url_base}/files/{file_id}"

        async def _reader(resp):
            if resp.status == 200:
                if reader:
                    return await reader(resp)
                return await resp.read()
            raise await upstream_exception_from_response(resp, url=url)

        return await self.request_executor.get(
            url=url,
            default_reader=_reader,
            **kwargs,
        )

    async def remove(self, file_id: str, **kwargs):
        """
        See description in
        [files.remove_file](@yw-nav-func:youwol.backends.files.root_paths.remove_file).
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/files/{file_id}",
            default_reader=json_reader,
            **kwargs,
        )
