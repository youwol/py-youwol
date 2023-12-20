# standard library
import asyncio

from dataclasses import dataclass

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.environment.upload_assets.models import UploadTask

# Youwol utilities
from youwol.utils import YouwolHeaders
from youwol.utils.context import Context


@dataclass
class UploadCustomAssetTask(UploadTask):
    async def get_raw(self, context: Context) -> tuple[bytes, dict[str, str]]:
        async with context.start(action="UploadCustomAssetTask.get_raw") as ctx:
            env = await context.get("env", YouwolEnvironment)
            asset_client = LocalClients.get_assets_client(env=env)
            headers = {**ctx.headers(), YouwolHeaders.py_youwol_local_only: "true"}
            data = await asyncio.gather(
                asset_client.get_zip_files(asset_id=self.asset_id, headers=headers),
                asset_client.get_asset(asset_id=self.asset_id, headers=headers),
            )
            return data

    async def create_raw(
        self, data: tuple[bytes, dict[str, str]], folder_id: str, context: Context
    ):
        async with context.start(action="UploadDataTask.create_raw") as ctx:
            assets_backend = self.remote_assets_gtw.get_assets_backend_router()
            await assets_backend.create_asset(
                body=data[1], params={"folder-id": folder_id}, headers=ctx.headers()
            )
            await assets_backend.add_zip_files(
                asset_id=self.asset_id, data=data[0], headers=ctx.headers()
            )

    async def update_raw(
        self, data: tuple[bytes, dict[str, str]], folder_id: str, context: Context
    ):
        async with context.start(action="UploadDataTask.update_raw") as ctx:
            assets_backend = self.remote_assets_gtw.get_assets_backend_router()
            await assets_backend.add_zip_files(
                asset_id=self.asset_id, data=data[0], headers=ctx.headers()
            )
