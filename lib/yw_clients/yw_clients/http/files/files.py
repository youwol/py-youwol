# standard library
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# typing
from typing import Any, cast

# third parties
from aiohttp import ClientResponse, FormData

# Youwol clients
from yw_clients.http.aiohttp_utils import (
    AioHttpExecutor,
    EmptyResponse,
    ParsedResponseT,
    json_reader,
    typed_reader,
)
from yw_clients.http.assets_gateway.models import NewAssetResponse
from yw_clients.http.files.models import (
    GetInfoResponse,
    PostFileResponse,
    PostMetadataBody,
)


@dataclass(frozen=True)
class FilesClient:
    """
    HTTP client of the :mod:`files <youwol.backends.files>` service.
    """

    url_base: str
    """
    Base URL used for the request.
    """

    request_executor: AioHttpExecutor
    """
    Request executor.
    """

    async def upload(
        self,
        content: bytes,
        filename: str,
        headers: dict[str, str],
        content_type: str | None = None,
        content_encoding: str | None = None,
        file_id: str | None = None,
        **kwargs,
    ) -> PostFileResponse | NewAssetResponse[PostFileResponse]:
        """
        See description in
        :func:`files.upload <youwol.backends.files.root_paths.upload>`.

        Warning:
            When proxied by the assets-gateway service, the `params` parameters (URL query parameters) need
            to feature a `folder-id` value: the destination folder ID of the created asset within the explorer.
            In this case the return type is `NewAssetResponse[PostFileResponse]`.
        """
        form_data = FormData()
        form_data.add_field("file", content, filename=filename, content_type="identity")
        form_data.add_field("file_name", filename)
        if content_type:
            form_data.add_field("content_type", content_type)
        if content_encoding:
            form_data.add_field("content_encoding", content_encoding)
        if file_id:
            form_data.add_field("file_id", file_id)

        is_wrapped = "params" in kwargs and "folder-id" in kwargs.get("params", {})

        resp = cast(
            dict[str, Any],
            await self.request_executor.post(
                url=f"{self.url_base}/files",
                reader=json_reader,
                data=form_data,
                headers=headers,
                **kwargs,
            ),
        )
        if is_wrapped:
            raw_resp = PostFileResponse(**resp["rawResponse"])
            del resp["rawResponse"]
            asset_resp = NewAssetResponse(**resp, rawResponse=raw_resp)
            return asset_resp

        return PostFileResponse(**resp)

    async def get_info(
        self, file_id: str, headers: dict[str, str], **kwargs
    ) -> GetInfoResponse:
        """
        See description in
        :func:`files.get_info <youwol.backends.files.root_paths.get_info>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/files/{file_id}/info",
            reader=typed_reader(GetInfoResponse),
            headers=headers,
            **kwargs,
        )

    async def update_metadata(
        self, file_id: str, body: PostMetadataBody, headers: dict[str, str], **kwargs
    ) -> EmptyResponse:
        """
        See description in
        :func:`files.update_metadata <youwol.backends.files.root_paths.update_metadata>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/files/{file_id}/metadata",
            reader=typed_reader(EmptyResponse),
            json=body.dict(),
            headers=headers,
            **kwargs,
        )

    async def get(
        self,
        file_id: str,
        headers: dict[str, str],
        reader: Callable[[ClientResponse], Awaitable[ParsedResponseT]],
        **kwargs,
    ) -> ParsedResponseT:
        """
        See description in
        :func:`files.get_file <youwol.backends.files.root_paths.get_file>`.
        """
        url = f"{self.url_base}/files/{file_id}"

        return await self.request_executor.get(
            url=url,
            reader=reader,
            headers=headers,
            **kwargs,
        )

    async def remove(
        self, file_id: str, headers: dict[str, str], **kwargs
    ) -> EmptyResponse:
        """
        See description in
        :func:`files.remove_file <youwol.backends.files.root_paths.remove_file>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/files/{file_id}",
            reader=typed_reader(EmptyResponse),
            headers=headers,
            **kwargs,
        )
