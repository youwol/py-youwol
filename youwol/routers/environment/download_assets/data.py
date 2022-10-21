import asyncio
from dataclasses import dataclass

from aiohttp import FormData
from fastapi import HTTPException

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.download_assets.common import create_asset_local
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils import Context
from youwol_utils.clients.assets.assets import AssetsClient


@dataclass
class DownloadDataTask(DownloadTask):

    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self, context: Context):
        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)
        local_assets: AssetsClient = LocalClients.get_assets_client(env=env)
        try:
            await local_assets.get(asset_id=self.asset_id, headers=context.headers())
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            else:
                raise e

    async def create_local_asset(self, context: Context):

        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)
        remote_gtw = await RemoteClients.get_assets_gateway_client(remote_host=env.selectedRemote,
                                                                   context=context)
        default_drive = await env.get_default_drive(context=context)

        async def get_raw_data(_ctx):
            data, metadata = await asyncio.gather(
                remote_gtw.get_files_backend_router().get(file_id=self.raw_id, headers=_ctx.headers()),
                remote_gtw.get_files_backend_router().get_info(file_id=self.raw_id, headers=_ctx.headers()),
            )
            return {"data": data, "metadata": metadata['metadata']}

        async def post_raw_data(folder_id: str, raw_data, ctx: Context):
            data = raw_data["data"]
            metadata = raw_data["metadata"]
            form_data = FormData()
            form_data.add_field(name='file', value=data, filename=metadata['fileName'],
                                content_type=metadata['contentType'])

            form_data.add_field('content_type', metadata['contentType'])
            form_data.add_field('content_encoding', metadata['contentEncoding'])
            form_data.add_field('file_id', self.raw_id)
            form_data.add_field('file_name',  metadata['fileName'])

            resp = await LocalClients\
                .get_assets_gateway_client(env=env)\
                .get_files_backend_router().upload(data=form_data, params={'folder-id': folder_id},
                                                   headers=ctx.headers())
            return resp

        await create_asset_local(
            asset_id=self.asset_id,
            kind='data',
            default_owning_folder_id=default_drive.downloadFolderId,
            get_raw_data=get_raw_data,
            post_raw_data=post_raw_data,
            context=context
            )
