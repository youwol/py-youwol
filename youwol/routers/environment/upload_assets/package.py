from dataclasses import dataclass
from typing import List, NamedTuple, Optional

from fastapi import HTTPException
from pydantic import BaseModel

from youwol.environment.clients import RemoteClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.upload_assets.models import UploadTask
from youwol_utils import decode_id
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json


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


def get_local_package(asset_id: str, config: YouwolEnvironment) -> Library:
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


def get_zip_path(asset_id: str, version, env: YouwolEnvironment):
    library_name = decode_id(decode_id(asset_id))
    base_path = env.pathsBook.local_storage / "cdn" / "youwol-users" / "libraries"
    namespace = None if '/' not in library_name else library_name.split('/')[0][1:]
    library_name = library_name if '/' not in library_name else library_name.split('/')[1]
    library_path = base_path / library_name / version \
        if not namespace \
        else base_path / namespace / library_name / version

    return library_name, library_path / "__original.zip"


class UploadPackageOptions(NamedTuple):
    """
    If provided, only these versions will be considered to publish
    """
    versions: Optional[List[str]] = None


@dataclass
class UploadPackageTask(UploadTask):

    async def get_raw(self):
        env = await self.context.get('env', YouwolEnvironment)
        async with self.context.start(action="UploadPackageTask.get_raw") as ctx:  # type: Context

            local_package = get_local_package(asset_id=self.asset_id, config=env)
            assets_gateway_client = await RemoteClients.get_assets_gateway_client(context=self.context)

            to_sync_releases = [v.version for v in local_package.releases]
            if self.options and self.options.versions:
                to_sync_releases = [v for v in to_sync_releases if v in self.options.versions]
            try:
                raw_metadata = await assets_gateway_client.get_raw_metadata(
                    kind='package',
                    raw_id=decode_id(self.asset_id),
                    headers=ctx.headers())
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
            if self.options and self.options.versions:
                to_sync_releases = [v for v in to_sync_releases if v in self.options.versions]

            await self.context.info(text="package's versions to sync. resolved",
                                    data={"missing": missing, "mismatch": mismatch})

            return to_sync_releases

    async def publish_version(self, folder_id: str, version: str):

        remote_gtw = await RemoteClients.get_assets_gateway_client(self.context)
        env = await self.context.get('env', YouwolEnvironment)
        async with self.context.start(action="Sync") as ctx:  # type: Context

            if self.options.versions and version not in self.options.versions:
                await ctx.info(text=f"Version '{version}' not in explicit versions provided",
                               data={"explicit versions": self.options.versions})
                return

            library_name, zip_path = get_zip_path(asset_id=self.asset_id, version=version, env=env)

            try:
                data = {'file': zip_path.read_bytes(), 'content_encoding': 'identity'}
                await remote_gtw.put_asset_with_raw(kind='package', folder_id=folder_id, data=data,
                                                    timeout=60000, headers=ctx.headers())
            finally:
                await ctx.info(
                    text=f"{library_name}#{version}: synchronization done"
                )
                # await check_package_status(package=local_package, context=context, target_versions=[version])

    async def create_raw(self, data: List[str], folder_id: str):

        versions = data
        for version in versions:
            await self.publish_version(folder_id=folder_id, version=version)

    async def update_raw(self, data: List[str], folder_id: str):

        await self.create_raw(data=data, folder_id=folder_id)
