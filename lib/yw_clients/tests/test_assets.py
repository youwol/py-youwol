# standard library
from pathlib import Path

# third parties
import pytest
import requests

# Youwol clients
from yw_clients import AioHttpExecutor, EmptyResponse, YouwolHeaders, bytes_reader
from yw_clients.http.assets import (
    AccessInfoResp,
    AccessPolicyBody,
    AccessPolicyResp,
    AddFilesResponse,
    AssetResponse,
    NewAssetBody,
    PermissionsResp,
    ReadPolicyEnum,
    SharePolicyEnum,
    UpdateAssetBody,
)
from yw_clients.http.assets_gateway import AssetsGatewayClient

headers = {YouwolHeaders.py_youwol_local_only: "true"}


@pytest.mark.asyncio
class TestAssetsClient:
    client = AssetsGatewayClient(
        url_base="http://localhost:2001/api/assets-gateway",
        request_executor=AioHttpExecutor(),
    ).assets()

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

        asset = await self.client.create_asset(
            body=NewAssetBody(
                rawId="test-asset-raw-id", kind="pytest", name="test-asset"
            ),
            headers=headers,
        )
        assert isinstance(asset, AssetResponse)
        asset = await self.client.get_asset(asset_id=asset.assetId, headers=headers)
        assert isinstance(asset, AssetResponse)
        asset = await self.client.update_asset(
            asset_id=asset.assetId,
            body=UpdateAssetBody(name="renamed"),
            headers=headers,
        )
        assert isinstance(asset, AssetResponse)
        image_filename = "logo.png"
        with open(
            Path(__file__).parent / "test-data" / "logo_YouWol_2020.png", "rb"
        ) as file:
            asset = await self.client.post_image(
                asset_id=asset.assetId,
                filename=image_filename,
                src=file.read(),
                headers=headers,
            )
        assert isinstance(asset, AssetResponse)
        media = await self.client.get_media(
            asset_id=asset.assetId,
            media_type="thumbnails",
            name=image_filename,
            reader=bytes_reader,
            headers=headers,
        )
        assert isinstance(media, bytes)
        asset = await self.client.remove_image(
            asset_id=asset.assetId, filename=image_filename, headers=headers
        )
        assert isinstance(asset, AssetResponse)
        with open(
            Path(__file__).parent / "test-data" / "test-add-files.zip", "rb"
        ) as file:
            files = await self.client.add_zip_files(
                asset_id=asset.assetId,
                data=file.read(),
                headers=headers,
            )
        assert isinstance(files, AddFilesResponse)
        file_resp = await self.client.get_file(
            asset_id=asset.assetId,
            path="innerFolder/innerFile.json",
            reader=bytes_reader,
            headers=headers,
        )
        assert isinstance(file_resp, bytes)
        zipfile = await self.client.get_zip_files(
            asset_id=asset.assetId, headers=headers
        )
        assert isinstance(zipfile, bytes)
        empty_resp = await self.client.delete_files(
            asset_id=asset.assetId, headers=headers
        )
        assert isinstance(empty_resp, EmptyResponse)

        access = await self.client.get_access_info(
            asset_id=asset.assetId, headers=headers
        )
        assert isinstance(access, AccessInfoResp)
        access_policy = await self.client.get_access_policy(
            asset_id=asset.assetId, group_id=default_drive.groupId, headers=headers
        )
        assert isinstance(access_policy, AccessPolicyResp)
        permissions = await self.client.get_permissions(
            asset_id=asset.assetId, headers=headers
        )
        assert isinstance(permissions, PermissionsResp)

        empty_resp = await self.client.put_access_policy(
            asset_id=asset.assetId,
            group_id="some-group",
            body=AccessPolicyBody(
                read=ReadPolicyEnum.AUTHORIZED, share=SharePolicyEnum.AUTHORIZED
            ),
            headers=headers,
        )
        assert isinstance(empty_resp, EmptyResponse)
        empty_resp = await self.client.delete_access_policy(
            asset_id=asset.assetId, group_id="some-group", headers=headers
        )
        assert isinstance(empty_resp, EmptyResponse)
        empty_resp = await self.client.delete_asset(
            asset_id=asset.assetId, headers=headers
        )
        assert isinstance(empty_resp, EmptyResponse)
