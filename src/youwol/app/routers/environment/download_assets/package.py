# standard library
from dataclasses import dataclass

# third parties
from fastapi import HTTPException

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.commons import Label
from youwol.app.routers.local_cdn.implementation import download_package

# Youwol utilities
from youwol.utils import CdnClient, Context, decode_id, encode_id

# relative
from .models import DownloadTask


@dataclass
class DownloadPackageTask(DownloadTask):
    def __post_init__(self):
        if "/api/assets-gateway/raw/" in self.url:
            self.version = self.url.split("/api/assets-gateway/raw/")[1].split("/")[2]
        if "/api/assets-gateway/cdn-backend/resources/" in self.url:
            self.version = self.url.split("/api/assets-gateway/cdn-backend/resources/")[
                1
            ].split("/")[1]

        self.package_name = decode_id(self.raw_id)

    def download_id(self):
        return self.package_name + "/" + self.version

    async def is_local_up_to_date(self, context: Context):
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        local_cdn: CdnClient = LocalClients.get_cdn_client(env=env)
        headers = context.headers()
        try:
            await local_cdn.get_version_info(
                library_id=encode_id(self.package_name),
                version=self.version,
                headers=headers,
            )
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            raise e

    async def create_local_asset(self, context: Context):
        async with context.start(
            action=f"DownloadPackageTask.create_local_asset {self.package_name}#{self.version}",
            with_labels=[str(Label.PACKAGE_DOWNLOADING)],
            with_attributes={
                "packageName": self.package_name,
                "packageVersion": self.version,
            },
        ) as ctx:
            await download_package(
                package_name=self.package_name,
                version=self.version,
                check_update_status=False,
                context=ctx,
            )
