import asyncio
from dataclasses import dataclass

from aiohttp import FormData

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.upload_assets.models import UploadTask
from youwol_utils import YouwolHeaders
from youwol_utils.context import Context


@dataclass
class UploadDataTask(UploadTask):

    async def get_raw(self, context: Context) -> FormData:
        # a dedicated asset service for data should be available and used here instead of assets_gateway_client
        async with context.start(action="UploadDataTask.get_raw") as ctx:  # type: Context
            env = await context.get('env', YouwolEnvironment)
            asset_client = LocalClients.get_assets_client(env=env)
            files_client = LocalClients.get_files_client(env=env)
            headers = {**ctx.headers(), YouwolHeaders.py_youwol_local_only: "true"}
            data, asset, info = await asyncio.gather(
                files_client.get(file_id=self.raw_id, headers=headers),
                asset_client.get_asset(asset_id=self.asset_id, headers=headers),
                files_client.get_info(file_id=self.raw_id, headers=headers)
                )
            form_data = FormData()
            form_data.add_field(name='file', value=data, filename=asset['name'],
                                content_type=info['metadata']['contentType'])
            form_data.add_field('rawId', self.raw_id)
            form_data.add_field('file_id', self.raw_id)
            form_data.add_field('file_name', asset['name'])
            return form_data

    async def create_raw(self, data: FormData, folder_id: str, context: Context):

        async with context.start(action="UploadDataTask.create_raw") as ctx:  # type: Context
            files_client = await RemoteClients.get_gtw_files_client(context=ctx)
            await files_client.upload(data=data, params={"folder-id": folder_id}, headers=ctx.headers())

    async def update_raw(self, data: bytes, folder_id: str, context: Context):

        async with context.start(action="UploadDataTask.update_raw") as ctx:  # type: Context
            remote_gtw = await RemoteClients.get_assets_gateway_client(context=ctx)
            await remote_gtw.update_raw_asset(
                kind='data',
                raw_id=self.raw_id,
                data=data,
                rest_of_path="content",
                headers=ctx.headers()
                )
