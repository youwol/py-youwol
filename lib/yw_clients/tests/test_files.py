# standard library
from pathlib import Path

# typing
from typing import cast

# third parties
import pytest
import requests

# Youwol clients
from yw_clients import AioHttpExecutor, EmptyResponse, YouwolHeaders, bytes_reader
from yw_clients.http.assets_gateway import AssetsGatewayClient
from yw_clients.http.assets_gateway.models import NewAssetResponse
from yw_clients.http.files import GetInfoResponse, PostFileResponse, PostMetadataBody

headers = {YouwolHeaders.py_youwol_local_only: "true"}


@pytest.mark.asyncio
class TestFilesClient:
    client = AssetsGatewayClient(
        url_base="http://localhost:2001/api/assets-gateway",
        request_executor=AioHttpExecutor(),
    ).files()

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
        with open(Path(__file__).parent / "test-data" / ".gitignore", "rb") as file:
            resp = cast(
                NewAssetResponse[PostFileResponse],
                await self.client.upload(
                    content=file.read(),
                    filename=".gitignore",
                    headers=headers,
                    params={"folder-id": default_drive.homeFolderId},
                ),
            )
        assert isinstance(resp, NewAssetResponse)
        file_id = resp.rawResponse.fileId
        info = await self.client.get_info(file_id=file_id, headers=headers)
        assert isinstance(info, GetInfoResponse)
        empty_resp = await self.client.update_metadata(
            file_id=file_id,
            body=PostMetadataBody(contentType="text"),
            headers=headers,
        )
        assert isinstance(empty_resp, EmptyResponse)
        file_resp = await self.client.get(
            file_id=file_id, reader=bytes_reader, headers=headers
        )
        assert isinstance(file_resp, bytes)
        empty_resp = await self.client.remove(file_id=file_id, headers=headers)
        assert isinstance(empty_resp, EmptyResponse)
