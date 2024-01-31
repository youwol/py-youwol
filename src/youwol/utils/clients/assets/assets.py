# standard library
from collections.abc import Awaitable
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Any, Callable, Optional, Union

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
    HTTP client of the [assets](@yw-nav-mod:youwol.backends.assets) service.
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
            url=f"{self.url_base}/healthz", default_reader=json_reader, **kwargs
        )

    async def create_asset(self, body, **kwargs):
        """
        See description in
        [assets.create_asset](@yw-nav-func:youwol.backends.assets.root_paths.create_asset).

        Warning:
            When used through the
            <a href="@yw-nav-func:youwol.utils.clients.assets_gateway.AssetsGatewayClient.get_assets_backend_router">
            assets-gateway client
            </a>,
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
        [assets.add_zip_files](@yw-nav-func:youwol.backends.assets.root_paths.add_zip_files).
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
        path: Union[Path, str],
        **kwargs,
    ):
        """
        See description in
        [assets.get_file](@yw-nav-func:youwol.backends.assets.root_paths.get_file).
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files/{path}",
            default_reader=auto_reader,
            **kwargs,
        )

    async def delete_files(self, asset_id: str, **kwargs):
        """
        See description in
        [assets.delete_files](@yw-nav-func:youwol.backends.assets.root_paths.delete_files).
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/files",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_zip_files(self, asset_id: str, **kwargs):
        """
        See description in
        [assets.get_zip_files](@yw-nav-func:youwol.backends.assets.root_paths.get_zip_files).
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files",
            default_reader=bytes_reader,
            **kwargs,
        )

    async def update_asset(self, asset_id: str, body, **kwargs):
        """
        See description in
        [assets.post_asset](@yw-nav-func:youwol.backends.assets.root_paths.post_asset).
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
        [assets.put_access_policy](@yw-nav-func:youwol.backends.assets.root_paths.put_access_policy).
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
        [assets.delete_access_policy](@yw-nav-func:youwol.backends.assets.root_paths.delete_access_policy).
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def post_image(self, asset_id: str, filename: str, src: bytes, **kwargs):
        """
        See description in
        [assets.post_image](@yw-nav-func:youwol.backends.assets.root_paths.post_image).
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
        [assets.remove_image](@yw-nav-func:youwol.backends.assets.root_paths.remove_image).
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
        reader: Optional[Callable[[ClientResponse], Awaitable[Any]]] = None,
        **kwargs,
    ):
        """
        See description in
        [assets.get_media_image](@yw-nav-func:youwol.backends.assets.root_paths.get_media_image) or
        [assets.get_media_thumbnail](@yw-nav-func:youwol.backends.assets.root_paths.get_media_thumbnail).
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
        [assets.get_asset](@yw-nav-func:youwol.backends.assets.root_paths.get_asset).
        """
        return await self.get(asset_id=asset_id, **kwargs)

    async def delete_asset(self, asset_id: str, **kwargs):
        """
        See description in
        [assets.delete_asset](@yw-nav-func:youwol.backends.assets.root_paths.delete_asset).
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_access_policy(self, asset_id: str, group_id: str, **kwargs):
        """
        See description in
        [assets.get_access_policy](@yw-nav-func:youwol.backends.assets.root_paths.get_access_policy).
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_permissions(self, asset_id: str, **kwargs):
        """
        See description in
        [assets.get_permissions](@yw-nav-func:youwol.backends.assets.root_paths.get_permissions).
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/permissions",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_access_info(self, asset_id: str, **kwargs):
        """
        See description in
        [assets.access_info](@yw-nav-func:youwol.backends.assets.root_paths.access_info).
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
