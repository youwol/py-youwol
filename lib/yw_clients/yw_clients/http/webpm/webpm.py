# standard library
import functools

from dataclasses import dataclass

# third parties
from aiohttp import FormData

from yw_clients.http.assets_gateway.models import NewAssetResponse
# Youwol clients
from yw_clients.http.request_executor import (
    EmptyResponse,
    FileResponse,
    RequestExecutor,
)
from yw_clients.http.webpm.models import (
    DeleteLibraryResponse,
    ExplorerResponse,
    Library,
    ListVersionsResponse,
    LoadingGraphBody,
    LoadingGraphResponseV1,
    PublishResponse,
)


@dataclass(frozen=True)
class WebpmClient:
    """
    HTTP client of the :mod:`cdn <youwol.backends.cdn>` service.
    """

    url_base: str
    """
    Base URL used for the request.
    """

    request_executor: RequestExecutor
    """
    Request executor.
    """

    @property
    def libraries_url(self):
        return f"{self.url_base}/queries/libraries"

    @property
    def loading_graph_url(self):
        return f"{self.url_base}/queries/loading-graph"

    @property
    def publish_url(self):
        return f"{self.url_base}/publish-library"

    @property
    def download_url(self):
        return f"{self.url_base}/download-library"

    @property
    def push_url(self):
        return f"{self.url_base}/publish_libraries"

    async def query_loading_graph(
        self, body: LoadingGraphBody, headers: dict[str, str], **kwargs
    ) -> LoadingGraphResponseV1:
        """
        See description in
        :func:`cdn.resolve_loading_tree <youwol.backends.cdn.root_paths.resolve_loading_tree>`.
        """
        return await self.request_executor.post(
            url=self.loading_graph_url,
            reader=self.request_executor.typed_reader(LoadingGraphResponseV1),
            json=body.dict(),
            headers=headers,
            **kwargs,
        )

    async def get_library_info(
        self,
        library_id: str,
        headers: dict[str, str],
        semver: str | None = None,
        max_count: int | None = None,
        **kwargs,
    ) -> ListVersionsResponse:
        """
        See description in
        :func:`cdn.get_library_info <youwol.backends.cdn.root_paths.get_library_info>`.
        """
        query_params = [
            (k, v)
            for k, v in {"semver": semver, "max-count": max_count}.items()
            if v is not None
        ]
        suffix = functools.reduce(
            lambda acc, item: acc + f"{acc}{item[0]}={item[1]}&", query_params, ""
        )

        url = f"{self.url_base}/libraries/{library_id}?{suffix}"
        return await self.request_executor.get(
            url=url,
            reader=self.request_executor.typed_reader(ListVersionsResponse),
            headers=headers,
            **kwargs,
        )

    async def get_version_info(
        self, library_id: str, version: str, headers: dict[str, str], **kwargs
    ) -> Library:
        """
        See description in
        :func:`cdn.get_version_info <youwol.backends.cdn.root_paths.get_version_info>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/libraries/{library_id}/{version}",
            reader=self.request_executor.typed_reader(Library),
            headers=headers,
            **kwargs,
        )

    async def publish(
        self, zip_content: bytes, headers: dict[str, str], **kwargs
    ) -> PublishResponse | NewAssetResponse[PublishResponse]:
        """
        See description in
        :func:`cdn.publish_library <youwol.backends.cdn.root_paths.publish_library>`.

        Warning:
            When proxied by the assets-gateway service, the `params` parameters (URL query parameters) need
            to feature a `folder-id` value: the destination folder ID of the created asset within the explorer.
            In this case the return type is `NewAssetResponse[PublishResponse]`.
        """
        form_data = FormData()
        form_data.add_field(
            "file", zip_content, filename="cdn.zip", content_type="identity"
        )
        is_wrapped = 'params' in kwargs and 'folder-id' in kwargs.get('params')
        resp = await self.request_executor.post(
            url=self.publish_url,
            data=form_data,
            reader=self.request_executor.json_reader,
            headers=headers,
            **kwargs,
        )
        if is_wrapped:
            raw_resp = PublishResponse(**resp['rawResponse'])
            asset_resp = NewAssetResponse(**resp)
            asset_resp.rawResponse = raw_resp
            return asset_resp

        return PublishResponse(**resp)

    async def download_library(
        self, library_id: str, version: str, headers: dict[str, str], **kwargs
    ) -> FileResponse:
        """
        See description in
        :func:`cdn.download_library <youwol.backends.cdn.root_paths.download_library>`.
        """
        return await self.request_executor.get(
            url=f"{self.download_url}/{library_id}/{version}",
            reader=self.request_executor.file_reader,
            headers=headers,
            **kwargs,
        )

    async def delete_library(
        self, library_id: str, headers: dict[str, str], **kwargs
    ) -> DeleteLibraryResponse:
        """
        See description in
        :func:`cdn.delete_library <youwol.backends.cdn.root_paths.delete_library>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/libraries/{library_id}",
            reader=self.request_executor.typed_reader(DeleteLibraryResponse),
            headers=headers,
            **kwargs,
        )

    async def delete_version(
        self, library_id: str, version: str, headers: dict[str, str], **kwargs
    ) -> EmptyResponse:
        """
        See description in
        :func:`cdn.delete_version <youwol.backends.cdn.root_paths.delete_version>`.
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/libraries/{library_id}/{version}",
            reader=self.request_executor.typed_reader(EmptyResponse),
            headers=headers,
            **kwargs,
        )

    async def get_explorer(
        self,
        library_id: str,
        version: str,
        folder_path: str,
        headers: dict[str, str],
        **kwargs,
    ) -> ExplorerResponse:
        """
        See description in
        :func:`cdn.explorer <youwol.backends.cdn.root_paths.explorer>`.
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/explorer/{library_id}/{version}/{folder_path}",
            reader=self.request_executor.typed_reader(ExplorerResponse),
            headers=headers,
            **kwargs,
        )

    async def get_entry_point(
        self,
        library_id: str,
        version: str,
        headers: dict[str, str],
        **kwargs,
    ) -> FileResponse:
        """
        See description in
        :func:`cdn.get_entry_point <youwol.backends.cdn.root_paths.get_entry_point>`.
        """
        return await self.get_resource(
            library_id=library_id,
            version=version,
            rest_of_path="",
            headers=headers,
            **kwargs,
        )

    async def get_resource(
        self,
        library_id: str,
        version: str,
        rest_of_path: str,
        headers: dict[str, str],
        **kwargs,
    ) -> FileResponse:
        """
        See description in
        :func:`cdn.get_resource <youwol.backends.cdn.root_paths.get_resource>`.
        """
        url = (
            f"{self.url_base}/resources/{library_id}/{version}/{rest_of_path}"
            if rest_of_path
            else f"{self.url_base}/resources/{library_id}/{version}"
        )

        return await self.request_executor.get(
            url=url,
            reader=self.request_executor.file_reader,
            headers=headers,
            **kwargs,
        )
