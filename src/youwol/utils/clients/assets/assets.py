# standard library
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Any, Awaitable, Callable, Union

# third parties
from aiohttp import ClientResponse, FormData

# Youwol utilities
from youwol.utils.clients.request_executor import (
    RequestExecutor,
    auto_reader,
    bytes_reader,
    json_reader,
)
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class AssetsClient:
    url_base: str

    request_executor: RequestExecutor

    async def healthz(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz", default_reader=json_reader, **kwargs
        )

    async def create_asset(self, body, **kwargs):
        return await self.request_executor.put(
            url=f"{self.url_base}/assets",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def add_zip_files(self, asset_id: str, data: bytes, **kwargs):
        form_data = FormData()
        form_data.add_field(
            "file",
            data,
            filename="zipped-files.zip",
            content_type="application/octet-stream",
        )
        return await self.request_executor.post(
            url=f"{self.url_base}/assets/{asset_id}/files",
            default_reader=json_reader,
            data=form_data,
            **kwargs,
        )

    async def get_file(
        self,
        asset_id: str,
        path: Union[Path, str],
        **kwargs,
    ):
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files/{path}",
            default_reader=auto_reader,
            **kwargs,
        )

    async def delete_files(self, asset_id: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/files",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_zip_files(self, asset_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files",
            default_reader=bytes_reader,
            **kwargs,
        )

    async def update_asset(self, asset_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/assets/{asset_id}",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def put_access_policy(self, asset_id: str, group_id: str, body, **kwargs):
        return await self.request_executor.put(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def delete_access_policy(self, asset_id: str, group_id: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def post_image(self, asset_id: str, filename: str, src: bytes, **kwargs):
        form_data = FormData()
        form_data.add_field(
            "file", src, filename=filename, content_type="application/octet-stream"
        )

        return await self.request_executor.post(
            url=f"{self.url_base}/assets/{asset_id}/images/{filename}",
            default_reader=json_reader,
            data=form_data,
            **kwargs,
        )

    async def remove_image(self, asset_id: str, filename: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/images/{filename}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_media(
        self,
        asset_id: str,
        media_type: str,
        name: str,
        reader: Callable[[ClientResponse], Awaitable[Any]] = None,
        **kwargs,
    ):
        async def _reader(resp: ClientResponse):
            if resp.status == 200:
                if reader:
                    return await reader(resp)
                return resp.read()

            await raise_exception_from_response(resp, **kwargs)

        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/{media_type}/{name}",
            default_reader=_reader,
            **kwargs,
        )

    async def query(self, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/query",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def get(self, asset_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_asset(self, asset_id: str, **kwargs):
        return await self.get(asset_id=asset_id, **kwargs)

    async def delete_asset(self, asset_id: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_access_policy(self, asset_id: str, group_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_permissions(self, asset_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/permissions",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_access_info(self, asset_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/access-info",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_records(self, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/records",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def record_access(self, raw_id: str, **kwargs):
        return await self.request_executor.put(
            url=f"{self.url_base}/raw/access/{raw_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def query_latest_access(self, asset_id: str, max_count=100, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/raw/access/{asset_id}/query-latest",
            default_reader=json_reader,
            params={"max-count": max_count},
            **kwargs,
        )
