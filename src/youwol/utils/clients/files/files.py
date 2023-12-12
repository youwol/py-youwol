# standard library
from dataclasses import dataclass

# typing
from typing import Any, Awaitable, Callable

# third parties
from aiohttp import ClientResponse

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class FilesClient:
    url_base: str

    request_executor: RequestExecutor

    async def healthz(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz",
            default_reader=json_reader,
            **kwargs,
        )

    async def upload(self, data, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/files",
            default_reader=json_reader,
            data=data,
            **kwargs,
        )

    async def get_info(self, file_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/files/{file_id}/info",
            default_reader=json_reader,
            **kwargs,
        )

    async def update_metadata(self, file_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/files/{file_id}/metadata",
            default_reader=json_reader,
            json={k: v for k, v in body.items() if v},
            **kwargs,
        )

    async def get(
        self,
        file_id: str,
        reader: Callable[[ClientResponse], Awaitable[Any]] = None,
        **kwargs,
    ):
        url = f"{self.url_base}/files/{file_id}"

        async def _reader(resp):
            if resp.status == 200:
                if reader:
                    return await reader(resp)
                return await resp.read()
            await raise_exception_from_response(resp, url=url)

        return await self.request_executor.get(
            url=url,
            default_reader=_reader,
            **kwargs,
        )

    async def remove(self, file_id: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/files/{file_id}",
            default_reader=json_reader,
            **kwargs,
        )
