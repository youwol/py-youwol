# standard library
from dataclasses import dataclass

from aiohttp import FormData

from yw_clients.http.assets_gateway.models import NewAssetResponse
# Youwol clients
from yw_clients.http.files.models import (
    GetInfoResponse,
    PostFileResponse,
    PostMetadataBody,
)
from yw_clients.http.request_executor import (
    EmptyResponse,
    FileResponse,
    RequestExecutor,
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

    request_executor: RequestExecutor
    """
    Request executor.
    """

    async def upload(self, content: bytes, filename: str, headers: dict[str, str], content_type:str | None = None, content_encoding: str | None = None,file_id: str | None = None, **kwargs) -> PostFileResponse | NewAssetResponse[PostFileResponse]:
        """
        See description in
        :func:`files.upload <youwol.backends.files.root_paths.upload>`.

        Warning:
            When proxied by the assets-gateway service, the `params` parameters (URL query parameters) need
            to feature a `folder-id` value: the destination folder ID of the created asset within the explorer.
            In this case the return type is `NewAssetResponse[PostFileResponse]`.
        """
        form_data = FormData()
        form_data.add_field(
            "file", content, filename=filename, content_type="identity"
        )
        form_data.add_field(
            "file_name", filename
        )
        if content_type:
            form_data.add_field("content_type", content_type)
        if content_encoding:
            form_data.add_field("content_encoding", content_encoding)
        if file_id:
            form_data.add_field("file_id", file_id)

        is_wrapped = 'params' in kwargs and 'folder-id' in kwargs.get('params')

        resp = await self.request_executor.post(
            url=f"{self.url_base}/files",
            reader=self.request_executor.json_reader,
            data=form_data,
            headers=headers,
            **kwargs,
        )
        if is_wrapped:
            raw_resp = PostFileResponse(**resp['rawResponse'])
            asset_resp = NewAssetResponse(**resp)
            asset_resp.rawResponse = raw_resp
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
            reader=self.request_executor.typed_reader(GetInfoResponse),
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
            reader=self.request_executor.typed_reader(EmptyResponse),
            json=body.dict(),
            headers=headers,
            **kwargs,
        )

    async def get(
        self,
        file_id: str,
        headers: dict[str, str],
        **kwargs,
    ) -> FileResponse:
        """
        See description in
        :func:`files.get_file <youwol.backends.files.root_paths.get_file>`.
        """
        url = f"{self.url_base}/files/{file_id}"

        return await self.request_executor.get(
            url=url,
            reader=self.request_executor.file_reader,
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
            reader=self.request_executor.typed_reader(EmptyResponse),
            headers=headers,
            **kwargs,
        )
