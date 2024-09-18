# standard library
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Any, Literal

# third parties
from aiohttp import FormData

# Youwol clients
from yw_clients.http.aiohttp_utils import (
    AioHttpExecutor,
    AioHttpFileResponse,
    EmptyResponse,
)
from yw_clients.http.assets.models import (
    AccessInfoResp,
    AccessPolicyBody,
    AccessPolicyResp,
    AddFilesResponse,
    AssetResponse,
    NewAssetBody,
    PermissionsResp,
    UpdateAssetBody,
)


@dataclass(frozen=True)
class AssetsClient:
    """
    HTTP client of the :mod:`assets <youwol.backends.assets>` service.
    """

    url_base: str
    """
    Base URL used for the request.
    """

    request_executor: AioHttpExecutor
    """
    Request executor.
    """

    async def create_asset(
        self,
        body: NewAssetBody,
        headers: dict[str, str],
        **kwargs: dict[str, Any] | None,
    ) -> AssetResponse:
        """
        See description in
        :func:`assets.create_asset <youwol.backends.assets.routers.assets.create_asset>`.

        Warning:
            When used through the
            :meth:`yw_clients.http.assets_gateway.assets_gateway.AssetsGatewayClient.assets`,
             the `params` parameters (URL query parameters) need
            to feature a `folder-id` value: the destination folder ID of the created asset within the explorer.
        """
        return await self.request_executor.put(
            url=f"{self.url_base}/assets",
            reader=self.request_executor.typed_reader(AssetResponse),
            json=body.dict(),
            headers=headers,
            **kwargs,
        )

    async def add_zip_files(
        self, asset_id: str, data: bytes, headers: dict[str, str], **kwargs
    ) -> AddFilesResponse:
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
            reader=self.request_executor.typed_reader(AddFilesResponse),
            data=form_data,
            headers=headers,
            **kwargs,
        )

    async def get_file(
        self, asset_id: str, path: Path | str, headers: dict[str, str], **kwargs
    ) -> AioHttpFileResponse:
        """
        See description in
        :func:`assets.get_file <youwol.backends.assets.routers.files.get_file>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files/{path}",
            reader=self.request_executor.file_reader,
            headers=headers,
            **kwargs,
        )

    async def delete_files(
        self, asset_id: str, headers: dict[str, str], **kwargs
    ) -> EmptyResponse:
        """
        See description in
        :func:`assets.delete_files <youwol.backends.assets.routers.files.delete_files>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/files",
            reader=self.request_executor.typed_reader(EmptyResponse),
            headers=headers,
            **kwargs,
        )

    async def get_zip_files(
        self, asset_id: str, headers: dict[str, str], **kwargs
    ) -> AioHttpFileResponse:
        """
        See description in
        :func:`assets.get_zip_files <youwol.backends.assets.routers.files.get_zip_files>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/files",
            reader=self.request_executor.file_reader,
            headers=headers,
            **kwargs,
        )

    async def update_asset(
        self, asset_id: str, body: UpdateAssetBody, headers: dict[str, str], **kwargs
    ) -> AssetResponse:
        """
        See description in
        :func:`assets.post_asset <youwol.backends.assets.routers.assets.post_asset>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/assets/{asset_id}",
            json=body.dict(),
            reader=self.request_executor.typed_reader(AssetResponse),
            headers=headers,
            **kwargs,
        )

    async def put_access_policy(
        self,
        asset_id: str,
        group_id: str,
        body: AccessPolicyBody,
        headers: dict[str, str],
        **kwargs,
    ) -> EmptyResponse:
        """
        See description in
        :func:`assets.put_access_policy <youwol.backends.assets.routers.access.put_access_policy>`.
        """
        return await self.request_executor.put(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            reader=self.request_executor.typed_reader(EmptyResponse),
            json=body.dict(),
            headers=headers,
            **kwargs,
        )

    async def delete_access_policy(
        self, asset_id: str, group_id: str, headers: dict[str, str], **kwargs
    ) -> EmptyResponse:
        """
        See description in
        :func:`assets.delete_access_policy <youwol.backends.assets.routers.access.delete_access_policy>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            reader=self.request_executor.typed_reader(EmptyResponse),
            headers=headers,
            **kwargs,
        )

    async def post_image(
        self,
        asset_id: str,
        filename: str,
        src: bytes,
        headers: dict[str, str],
        **kwargs,
    ) -> AssetResponse:
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
            reader=self.request_executor.typed_reader(AssetResponse),
            data=form_data,
            headers=headers,
            **kwargs,
        )

    async def remove_image(
        self, asset_id: str, filename: str, headers: dict[str, str], **kwargs
    ) -> AssetResponse:
        """
        See description in
        :func:`assets.remove_image <youwol.backends.assets.routers.images.remove_image>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}/images/{filename}",
            reader=self.request_executor.typed_reader(AssetResponse),
            headers=headers,
            **kwargs,
        )

    async def get_media(
        self,
        asset_id: str,
        media_type: Literal["thumbnails", "images"],
        name: str,
        headers: dict[str, str],
        **kwargs,
    ) -> AioHttpFileResponse:
        """
        See description in
        :func:`assets.get_media_image <youwol.backends.assets.routers.images.get_media_image>` or
        :func:`assets.get_media_thumbnail <youwol.backends.assets.routers.images.get_media_thumbnail>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/{media_type}/{name}",
            reader=self.request_executor.file_reader,
            headers=headers,
            **kwargs,
        )

    async def get_asset(self, asset_id: str, headers: dict[str, str], **kwargs):
        """
        See description in
        :func:`assets.get_asset <youwol.backends.assets.routers.assets.get_asset>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}",
            reader=self.request_executor.typed_reader(AssetResponse),
            headers=headers,
            **kwargs,
        )

    async def delete_asset(
        self, asset_id: str, headers: dict[str, str], **kwargs
    ) -> EmptyResponse:
        """
        See description in
        :func:`assets.delete_asset <youwol.backends.assets.routers.assets.delete_asset>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/assets/{asset_id}",
            reader=self.request_executor.typed_reader(EmptyResponse),
            headers=headers,
            **kwargs,
        )

    async def get_access_policy(
        self, asset_id: str, group_id: str, headers: dict[str, str], **kwargs
    ) -> AccessPolicyResp:
        """
        See description in
        :func:`assets.get_access_policy <youwol.backends.assets.routers.access.get_access_policy>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/access/{group_id}",
            reader=self.request_executor.typed_reader(AccessPolicyResp),
            headers=headers,
            **kwargs,
        )

    async def get_permissions(
        self, asset_id: str, headers: dict[str, str], **kwargs
    ) -> PermissionsResp:
        """
        See description in
        :func:`assets.get_permissions <youwol.backends.assets.routers.permissions.get_permissions>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/permissions",
            reader=self.request_executor.typed_reader(PermissionsResp),
            headers=headers,
            **kwargs,
        )

    async def get_access_info(
        self, asset_id: str, headers: dict[str, str], **kwargs
    ) -> AccessInfoResp:
        """
        See description in
        :func:`assets.access_info <youwol.backends.assets.routers.permissions.access_info>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/assets/{asset_id}/access-info",
            reader=self.request_executor.typed_reader(AccessInfoResp),
            headers=headers,
            **kwargs,
        )
