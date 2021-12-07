from dataclasses import dataclass
from fastapi import HTTPException

from auto_download.auto_download_thread import decode_id
from auto_download.common import create_asset_local
from auto_download.models import DownloadTask
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
        local_cdn: CdnClient = self.context.config.localClients.cdn_client
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
        remote_gtw = await self.context.config.get_assets_gateway_client(context=self.context)
        default_owning_folder_id = (await self.context.config.get_default_drive()).systemPackagesFolderId
        await create_asset_local(
            asset_id=self.asset_id,
            kind='package',
            default_owning_folder_id=default_owning_folder_id,
            get_raw_data=lambda: remote_gtw.cdn_get_package(library_name=self.package_name, version=self.version),
            to_post_raw_data=lambda pack: {'file': pack},
            context=self.context
            )
