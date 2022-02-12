from dataclasses import dataclass

from fastapi import HTTPException

from youwol.environment.clients import LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.commons import Label
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol.routers.local_cdn.implementation import download_package
from youwol.web_socket import UserContextLogger
from youwol_utils import CdnClient, decode_id


@dataclass
class DownloadPackageTask(DownloadTask):

    def __post_init__(self):
        self.version = self.url.split('/api/assets-gateway/raw/')[1].split('/')[2]
        self.package_name = decode_id(self.raw_id)

    def download_id(self):
        return self.package_name+"/"+self.version

    async def is_local_up_to_date(self):
        env = await self.context.get('env', YouwolEnvironment)
        local_cdn: CdnClient = LocalClients.get_cdn_client(env=env)
        headers = self.context.headers()
        try:
            await local_cdn.get_package(
                library_name=self.package_name,
                version=self.version,
                metadata=True,
                headers=headers
            )
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            raise e

    async def create_local_asset(self):

        async with self.context.start(
                action=f"DownloadPackageTask.create_local_asset {self.package_name}#{self.version}",
                with_labels=[str(Label.PACKAGE_DOWNLOADING)],
                with_attributes={
                    'packageName': self.package_name,
                    'packageVersion': self.version,
                },
                with_loggers=[UserContextLogger()]
        ) as ctx:
            await download_package(package_name=self.package_name, version=self.version, check_update_status=False,
                                   context=ctx)
