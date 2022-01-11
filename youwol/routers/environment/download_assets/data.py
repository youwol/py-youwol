from dataclasses import dataclass
from fastapi import HTTPException
from youwol.environment.clients import RemoteClients, LocalClients
from youwol.routers.environment.download_assets.common import create_asset_local
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils.clients.assets.assets import AssetsClient


@dataclass
class DownloadDataTask(DownloadTask):

    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self):

        local_assets: AssetsClient = LocalClients.get_assets_client(context=self.context)
        try:
            await local_assets.get(asset_id=self.asset_id)
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            else:
                raise e

    async def create_local_asset(self):

        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        default_drive = await self.context.config.get_default_drive(context=self.context)

        await create_asset_local(
            asset_id=self.asset_id,
            kind='data',
            default_owning_folder_id=default_drive.downloadFolderId,
            get_raw_data=lambda: remote_gtw.get_raw(kind='data', raw_id=self.raw_id),
            to_post_raw_data=lambda data: {"file": data, "rawId": self.raw_id},
            context=self.context
            )
