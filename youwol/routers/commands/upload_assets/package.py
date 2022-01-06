from dataclasses import dataclass
from typing import List
from fastapi import HTTPException
from pydantic import BaseModel

from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.configuration.clients import RemoteClients
from youwol.context import Context
from youwol.models import Label
from youwol.routers.commands.upload_assets.models import UploadTask
from youwol.utils_paths import parse_json
from youwol_utils import decode_id


class TreeItem(BaseModel):
    name: str
    itemId: str
    group: str
    borrowed: bool
    rawId: str


class Release(BaseModel):
    version: str
    fingerprint: str


class Library(BaseModel):
    assetId: str
    libraryName: str
    namespace: str
    treeItems: List[TreeItem]
    releases: List[Release]
    rawId: str


def get_local_package(asset_id: str, config: YouwolConfiguration) -> Library:
    """
    Not populated with tree items
    """
    data_packages = parse_json(config.pathsBook.local_docdb / "cdn" / "libraries" / "data.json")
    raw_id = decode_id(asset_id)
    library_name = decode_id(raw_id)
    releases = [d for d in data_packages['documents'] if d['library_name'] == library_name]
    if not releases:
        raise HTTPException(status_code=404, detail=f'Local package {library_name} not found')

    return Library(
        libraryName=library_name,
        namespace=releases[0]["namespace"],
        releases=[Release(version=r['version'], fingerprint=r['fingerprint'] if 'fingerprint' in r else '')
                  for r in releases],
        assetId=asset_id,
        rawId=raw_id,
        treeItems=[],
        )


def get_zip_path(asset_id: str, version, context: Context):
    library_name = decode_id(decode_id(asset_id))
    base_path = context.config.pathsBook.local_storage / "cdn" / "youwol-users" / "libraries"
    namespace = None if '/' not in library_name else library_name.split('/')[0][1:]
    library_name = library_name if '/' not in library_name else library_name.split('/')[1]
    library_path = base_path / library_name / version \
        if not namespace \
        else base_path / namespace / library_name / version

    return library_name, library_path / "__original.zip"


@dataclass
class UploadPackageTask(UploadTask):

    async def get_raw(self):
        local_package = get_local_package(asset_id=self.asset_id, config=self.context.config)
        assets_gateway_client = await RemoteClients.get_assets_gateway_client(context=self.context)

        to_sync_releases = [v.version for v in local_package.releases]
        try:
            raw_metadata = await assets_gateway_client.get_raw_metadata(kind='package', raw_id=decode_id(self.asset_id))
        except HTTPException as e:
            if e.status_code == 404:
                return to_sync_releases
            raise e

        remote_versions = {release['version']: release['fingerprint'] for release in raw_metadata['releases']}
        local_versions = {release.version: release.fingerprint for release in local_package.releases}

        missing = [v for v in local_versions.keys() if v not in remote_versions]
        mismatch = [v for v, checksum in local_versions.items()
                    if v in remote_versions and checksum != remote_versions[v]]
        to_sync_releases = missing + mismatch
        await self.context.info(text="package's versions to sync. resolved",
                                data={"missing": missing, "mismatch": mismatch})

        return to_sync_releases

    async def publish_version(self, folder_id: str, version: str):

        remote_gtw = await RemoteClients.get_assets_gateway_client(self.context)
        async with self.context.start(action="Sync") as ctx:
            library_name, zip_path = get_zip_path(asset_id=self.asset_id, version=version, context=self.context)

            try:
                data = {'file': zip_path.read_bytes(), 'content_encoding': 'identity'}
                await remote_gtw.put_asset_with_raw(kind='package', folder_id=folder_id, data=data,
                                                    timeout=600)
            finally:
                await ctx.info(
                    labels=[Label.DONE],
                    text=f"{library_name}#{version}: synchronization done"
                    )
                # await check_package_status(package=local_package, context=context, target_versions=[version])

    async def create_raw(self, data: List[str], folder_id: str):

        versions = data
        for version in versions:
            await self.publish_version(folder_id=folder_id, version=version)

    async def update_raw(self, data: List[str], folder_id: str):

        versions = data

        for version in versions:
            await self.publish_version(folder_id=folder_id, version=version)
