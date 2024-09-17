# standard library
from dataclasses import dataclass

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

    async def upload(self, data, headers: dict[str, str], **kwargs) -> PostFileResponse:
        """
        See description in
        :func:`files.upload <youwol.backends.files.root_paths.upload>`.
        """
        return await self.request_executor.post(
            url=f"{self.url_base}/files",
            reader=self.request_executor.typed_reader(PostFileResponse),
            data=data,
            headers=headers,
            **kwargs,
        )

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
            json=body.json(),
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
