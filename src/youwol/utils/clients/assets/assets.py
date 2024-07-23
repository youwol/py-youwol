# standard library
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Any

# third parties
from aiohttp import ClientResponse, FormData

# Youwol utilities
from youwol.utils.clients.request_executor import (
    RequestExecutor,
    auto_reader,
    bytes_reader,
    json_reader,
)
from youwol.utils.exceptions import upstream_exception_from_response


@dataclass(frozen=True)
class AssetsClient:
    """
    HTTP client of the :mod:`assets <youwol.backends.assets>` service.
    """

    url_base: str
    """
    Base URL used for the request.
    """

    request_executor: RequestExecutor
    """
    Request executor.
    """

    async def create_asset(self, body, **kwargs):
        """
        See description in
        :func:`assets.create_asset <youwol.backends.assets.routers.assets.create_asset>`.

        Warning:
            When used through the
            :meth:`youwol.utils.clients.assets_gateway.assets_gateway.AssetsGatewayClient.get_assets_backend_router`,
             the `params` parameters (URL query parameters) need
            to feature a `folder-id` value: the destination folder ID of the created asset within the explorer.
        """
        return await self.request_executor.put(
            url=f"{self.url_base}/assets",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def add_zip_files(self, asset_id: str, data: bytes, **kwargs):
        """
        See description in
        :func:`assets.add_zip_files <youwol.backends.assets.routers.files.add_zip_files>`.
        """
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
        path: Path | str,
        **kwargs,
    ):
        """
        See description in
        :func:`assets.get_file <youwol.backends.assets.routers.files.get_file>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files/{path}",
            default_reader=auto_reader,
            **kwargs,
        )

    async def delete_files(self, asset_id: str, **kwargs):
        """
        See description in
        :func:`assets.delete_files <youwol.backends.assets.routers.files.delete_files>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/files",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_zip_files(self, asset_id: str, **kwargs):
        """
        See description in
        :func:`assets.get_zip_files <youwol.backends.assets.routers.files.get_zip_files>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files",
            default_reader=bytes_reader,
            **kwargs,
        )

    async def update_asset(self, asset_id: str, body, **kwargs):
        """
        See description in
        :func:`assets.post_asset <youwol.backends.assets.routers.assets.post_asset>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/assets/{asset_id}",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def put_access_policy(self, asset_id: str, group_id: str, body, **kwargs):
        """
        See description in
        :func:`assets.put_access_policy <youwol.backends.assets.routers.access.put_access_policy>`.
        """
        return await self.request_executor.put(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def delete_access_policy(self, asset_id: str, group_id: str, **kwargs):
        """
        See description in
        :func:`assets.delete_access_policy <youwol.backends.assets.routers.access.delete_access_policy>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def post_image(self, asset_id: str, filename: str, src: bytes, **kwargs):
        """
        See description in
        :func:`assets.post_image <youwol.backends.assets.routers.images.post_image>`.
        """
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
        """
        See description in
        :func:`assets.remove_image <youwol.backends.assets.routers.images.remove_image>`.
        """
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
        reader: Callable[[ClientResponse], Awaitable[Any]] | None = None,
        **kwargs,
    ):
        """
        See description in
        :func:`assets.get_media_image <youwol.backends.assets.routers.images.get_media_image>` or
        :func:`assets.get_media_thumbnail <youwol.backends.assets.routers.images.get_media_thumbnail>`.
        """

        async def _reader(resp: ClientResponse):
            if resp.status == 200:
                if reader:
                    return await reader(resp)
                return resp.read()

            raise await upstream_exception_from_response(resp, **kwargs)

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
        """
        See description in
        :func:`assets.get_asset <youwol.backends.assets.routers.assets.get_asset>`.
        """
        return await self.get(asset_id=asset_id, **kwargs)

    async def delete_asset(self, asset_id: str, **kwargs):
        """
        See description in
        :func:`assets.delete_asset <youwol.backends.assets.routers.assets.delete_asset>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_access_policy(self, asset_id: str, group_id: str, **kwargs):
        """
        See description in
        :func:`assets.get_access_policy <youwol.backends.assets.routers.access.get_access_policy>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_permissions(self, asset_id: str, **kwargs):
        """
        See description in
        :func:`assets.get_permissions <youwol.backends.assets.routers.permissions.get_permissions>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/permissions",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_access_info(self, asset_id: str, **kwargs):
        """
        See description in
        :func:`assets.access_info <youwol.backends.assets.routers.permissions.access_info>`.
        """
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
