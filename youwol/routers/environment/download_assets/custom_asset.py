from dataclasses import dataclass
from youwol.environment import LocalClients, YouwolEnvironment
from youwol.routers.environment.download_assets.common import create_asset_local, is_asset_in_local
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils import Context
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


async def sync_asset_files(asset_id: str, remote_gtw: AssetsGatewayClient, caller_context: Context):

    async with caller_context.start(action="Sync. files of asset") as ctx:  # type: Context

        env: YouwolEnvironment = await ctx.get('env', YouwolEnvironment)
        data = await remote_gtw.get_assets_backend_router().get_zip_files(asset_id=asset_id, headers=ctx.headers())
        metadata = await remote_gtw.get_assets_backend_router().get_asset(asset_id=asset_id, headers=ctx.headers())
        await LocalClients.get_assets_client(env=env) \
            .create_asset(body=metadata, headers=ctx.headers())
        await LocalClients.get_assets_client(env=env) \
            .add_zip_files(asset_id=asset_id, data=data, headers=ctx.headers())


@dataclass
class DownloadCustomAssetTask(DownloadTask):

    def download_id(self):
        return self.asset_id

    async def is_local_up_to_date(self, context: Context):
        return await is_asset_in_local(asset_id=self.asset_id, context=context)

    async def create_local_asset(self, context: Context):

        await create_asset_local(
            asset_id=self.asset_id,
            kind='custom-asset',
            sync_raw_data=sync_asset_files,
            context=context
        )
