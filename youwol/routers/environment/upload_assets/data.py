import asyncio
from dataclasses import dataclass
from aiohttp import FormData

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.upload_assets.models import UploadTask


@dataclass
class UploadDataTask(UploadTask):

    async def get_raw(self) -> FormData:
        # a dedicated asset service for data should be available and used here instead of assets_gateway_client
        env = await self.context.get('env', YouwolEnvironment)
        asset_gtw = LocalClients.get_assets_gateway_client(env=env)
        data, metadata, raw_metadata = await asyncio.gather(
            asset_gtw.get_raw(kind='data', raw_id=self.raw_id),
            asset_gtw.get_asset_metadata(asset_id=self.asset_id),
            asset_gtw.get_raw_metadata(kind='data', raw_id=self.raw_id)
            )
        form_data = FormData()
        form_data.add_field(name='file', value=data, filename=metadata['name'],
                            content_type=raw_metadata['contentType'])
        form_data.add_field('rawId', self.raw_id)
        return form_data

    async def create_raw(self, data: FormData, folder_id: str):

        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        await remote_gtw.put_asset_with_raw(kind='data', folder_id=folder_id, data=data)

    async def update_raw(self, data: bytes, folder_id: str):

        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        await remote_gtw.update_raw_asset(
            kind='data',
            raw_id=self.raw_id,
            data=data,
            rest_of_path="content"
            )
