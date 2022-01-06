from dataclasses import dataclass
from fastapi import HTTPException

from youwol.auto_download.auto_download_thread import decode_id
from youwol.auto_download.common import create_asset_local
from youwol.auto_download.models import DownloadTask
from youwol.configuration.clients import LocalClients, RemoteClients
from youwol_utils import CdnClient


@dataclass
class DownloadPackageTask(DownloadTask):

    def __post_init__(self):
        super()
        self.version = self.url.split('/api/assets-gateway/raw/')[1].split('/')[2]
        self.package_name = decode_id(self.raw_id)

    def download_id(self):
        return self.package_name+"/"+self.version

    async def is_local_up_to_date(self):
        local_cdn: CdnClient = LocalClients.get_cdn_client(context=self.context)
        try:
            await local_cdn.get_package(
                library_name=self.package_name,
                version=self.version,
                metadata=True
                )
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            raise e

    async def create_local_asset(self):
        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        default_drive = await self.context.config.get_default_drive(context=self.context)
        await create_asset_local(
            asset_id=self.asset_id,
            kind='package',
            default_owning_folder_id=default_drive.systemPackagesFolderId,
            get_raw_data=lambda: remote_gtw.cdn_get_package(library_name=self.package_name, version=self.version),
            to_post_raw_data=lambda pack: {'file': pack},
            context=self.context
            )
