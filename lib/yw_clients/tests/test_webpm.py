# standard library
from pathlib import Path

# typing
from typing import cast

# third parties
import pytest
import requests

# Youwol clients
from yw_clients import (
    AioHttpExecutor,
    EmptyResponse,
    YouwolHeaders,
    json_reader,
    text_reader,
)
from yw_clients.http.assets_gateway import AssetsGatewayClient
from yw_clients.http.assets_gateway.models import NewAssetResponse
from yw_clients.http.webpm import (
    DeleteLibraryResponse,
    ExplorerResponse,
    Library,
    ListVersionsResponse,
    LoadingGraphBody,
    LoadingGraphResponseV1,
    PublishResponse,
)

headers = {YouwolHeaders.py_youwol_local_only: "true"}


@pytest.mark.asyncio
class TestWebpmClient:
    client = AssetsGatewayClient(
        url_base="http://localhost:2001/api/assets-gateway",
        request_executor=AioHttpExecutor(),
    ).webpm()

    async def test_api(self) -> None:
        requests.post(
            url="http://localhost:2001/admin/custom-commands/reset", json={}, timeout=10
        )
        default_drive = (
            await AssetsGatewayClient(
                url_base="http://localhost:2001/api/assets-gateway",
                request_executor=AioHttpExecutor(),
            )
            .explorer()
            .get_default_user_drive(headers=headers)
        )
        with open(
            Path(__file__).parent / "test-data" / "rxjs#7.8.1" / "cdn.zip", "rb"
        ) as file:
            publish = cast(
                NewAssetResponse[PublishResponse],
                await self.client.publish(
                    zip_content=file.read(),
                    headers=headers,
                    params={"folder-id": default_drive.homeFolderId},
                ),
            )

        assert isinstance(publish, NewAssetResponse)
        library_id = publish.rawResponse.id
        library = await self.client.get_library_info(
            library_id=library_id, headers=headers
        )
        assert isinstance(library, ListVersionsResponse)
        version = await self.client.get_version_info(
            library_id=library_id, version="7.8.1", headers=headers
        )
        assert isinstance(version, Library)
        entry = await self.client.get_entry_point(
            library_id=library_id, version="7.8.1", reader=text_reader, headers=headers
        )
        assert isinstance(entry, str)
        resource = await self.client.get_resource(
            library_id=library_id,
            version="7.8.1",
            rest_of_path="package.json",
            reader=json_reader,
            headers=headers,
        )
        assert isinstance(resource, dict)
        explorer = await self.client.get_explorer(
            library_id=library_id,
            version="7.8.1",
            folder_path="/",
            headers=headers,
        )
        assert isinstance(explorer, ExplorerResponse)
        loading_graph = await self.client.query_loading_graph(
            body=LoadingGraphBody(libraries={"rxjs": "^7.0.0"}), headers=headers
        )
        assert isinstance(loading_graph, LoadingGraphResponseV1)
        download = await self.client.download_library(
            library_id=library_id, version="7.8.1", headers=headers
        )
        assert isinstance(download, bytes)
        empty_resp = await self.client.delete_version(
            library_id=library_id, version="7.8.1", headers=headers
        )
        assert isinstance(empty_resp, EmptyResponse)
        delete = await self.client.delete_library(
            library_id=library_id, headers=headers
        )
        assert isinstance(delete, DeleteLibraryResponse)
