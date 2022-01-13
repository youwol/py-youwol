from dataclasses import dataclass

from fastapi import HTTPException

from youwol.environment.clients import LocalClients, RemoteClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.download_assets.common import create_asset_local
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils import CdnClient, decode_id


@dataclass
class DownloadPackageTask(DownloadTask):

    def __post_init__(self):
        super()
        self.version = self.url.split('/api/assets-gateway/raw/')[1].split('/')[2]
        self.package_name = decode_id(self.raw_id)

    def download_id(self):
        return self.package_name+"/"+self.version

    async def is_local_up_to_date(self):
        env = await self.context.get('env', YouwolEnvironment)
        local_cdn: CdnClient = LocalClients.get_cdn_client(env=env)
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

        env = await self.context.get('env', YouwolEnvironment)
        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        default_drive = await env.get_default_drive(context=self.context)
        await create_asset_local(
            asset_id=self.asset_id,
            kind='package',
            default_owning_folder_id=default_drive.systemPackagesFolderId,
            get_raw_data=lambda: remote_gtw.cdn_get_package(library_name=self.package_name, version=self.version),
            to_post_raw_data=lambda pack: {'file': pack},
            context=self.context
            )
