# standard library
import asyncio

from dataclasses import dataclass

# third parties
from aiohttp import FormData

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.environment.upload_assets.models import UploadTask

# Youwol utilities
from youwol.utils import YouwolHeaders
from youwol.utils.context import Context


@dataclass
class UploadDataTask(UploadTask):
    async def get_raw(self, context: Context) -> FormData:
        # a dedicated asset service for data should be available and used here instead of assets_gateway_client
        async with context.start(action="UploadDataTask.get_raw") as ctx:
            env = await context.get("env", YouwolEnvironment)
            asset_client = LocalClients.get_assets_client(env=env)
            files_client = LocalClients.get_files_client(env=env)
            headers = {**ctx.headers(), YouwolHeaders.py_youwol_local_only: "true"}
            data, asset, info = await asyncio.gather(
                files_client.get(file_id=self.raw_id, headers=headers),
                asset_client.get_asset(asset_id=self.asset_id, headers=headers),
                files_client.get_info(file_id=self.raw_id, headers=headers),
            )
            form_data = FormData()
            form_data.add_field(
                name="file",
                value=data,
                filename=asset["name"],
                content_type=info["metadata"]["contentType"],
            )
            form_data.add_field("rawId", self.raw_id)
            form_data.add_field("file_id", self.raw_id)
            form_data.add_field("file_name", asset["name"])
            return form_data

    async def create_raw(self, data: FormData, folder_id: str, context: Context):
        async with context.start(action="UploadDataTask.create_raw") as ctx:
            files_client = self.remote_assets_gtw.get_files_backend_router()
            await files_client.upload(
                data=data, params={"folder-id": folder_id}, headers=ctx.headers()
            )

    async def update_raw(self, data: bytes, folder_id: str, context: Context):
        async with context.start(action="UploadDataTask.update_raw") as ctx:
            await self.remote_assets_gtw.get_files_backend_router().upload(
                data=data, headers=ctx.headers()
            )
