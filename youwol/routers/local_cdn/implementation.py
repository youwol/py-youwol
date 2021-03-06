import asyncio
from itertools import groupby
from typing import NamedTuple, List

from fastapi import HTTPException

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.commons import Label
from youwol.routers.environment.download_assets.common import create_asset_local
from youwol.routers.local_cdn.models import CheckUpdateResponse, UpdateStatus, PackageVersionInfo, \
    DownloadedPackageResponse, DownloadPackageBody, PackageEventResponse, Event
from youwol_utils import encode_id
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json


class TargetPackage(NamedTuple):
    library_name: str
    library_id: str
    version: str
    version_number: int
    fingerprint: str

    @staticmethod
    def from_response(d):
        return TargetPackage(library_name=d['library_name'], library_id=d['library_id'], version=d['version'],
                             version_number=int(d['version_number']), fingerprint=d['fingerprint'])


def get_latest_local_cdn_version(env: YouwolEnvironment) -> List[TargetPackage]:

    db_path = parse_json(env.pathsBook.local_cdn_docdb)
    data = sorted(db_path['documents'], key=lambda d: d['library_name'])
    groups = [list(g) for _, g in groupby(data, key=lambda d: d['library_name'])]
    targets = [max(g, key=lambda d: int(d['version_number'])) for g in groups]

    return [TargetPackage.from_response(t) for t in targets]


async def check_update(
        local_package: TargetPackage,
        context: Context):

    remote_gtw_client = await RemoteClients.get_assets_gateway_client(context=context)
    headers = {
        "authorization": context.request.headers.get("authorization")
    }
    name, version = local_package.library_name, local_package.version
    async with context.start(
            action=f"Check update for {local_package.library_name}",
            on_enter=lambda ctx_enter: ctx_enter.send(
                PackageEventResponse(packageName=name, version=version, event=Event.updateCheckStarted)
            ),
            on_exit=lambda ctx_exit: ctx_exit.send(
                PackageEventResponse(packageName=name, version=version, event=Event.updateCheckDone)
            ),
            with_attributes={
                'event': 'check_update_pending',
                'packageName': name,
                'packageVersion': version,
            }
    ) as ctx:  # type: Context
        package_id = encode_id(local_package.library_name)

        try:
            remote_package = await remote_gtw_client.cdn_get_versions(package_id=package_id, headers=headers)
        except HTTPException as e:
            if e.status_code == 404:
                await ctx.info(text=f"{name} does not exist in remote")
            raise e
        await ctx.info(text=f"Retrieved remote info", data={'remote_package': remote_package})

        latest = remote_package['releases'][0]
        status = UpdateStatus.mismatch
        if latest['fingerprint'] == local_package.fingerprint:
            status = UpdateStatus.upToDate
        elif latest['version_number'] > local_package.version_number:
            status = UpdateStatus.remoteAhead
        elif latest['version_number'] < local_package.version_number:
            status = UpdateStatus.localAhead

        await ctx.info(text=f"Status: {str(status)}")
        response = CheckUpdateResponse(
            status=status,
            packageName=local_package.library_name,
            localVersionInfo=PackageVersionInfo(version=version,
                                                fingerprint=local_package.fingerprint),
            remoteVersionInfo=PackageVersionInfo(version=latest['version'], fingerprint=latest['fingerprint'])
        )
        await ctx.send(response)
        return response


async def check_updates_from_queue(
        queue: asyncio.Queue,
        all_updates: List[CheckUpdateResponse],
        context: Context):

    while not queue.empty():
        local_package: TargetPackage = queue.get_nowait()
        try:
            response = await check_update(local_package=local_package, context=context)
        except HTTPException as e:
            if e.status_code == 404:
                queue.task_done()
                return
            await context.error(text=f"Error occurred while checking {local_package.library_name}",
                                data={'detail': e.detail, "statusCode": e.status_code}
                                )
            raise e
        all_updates.append(response)
        queue.task_done()


async def download_packages_from_queue(
        queue: asyncio.Queue,
        check_update_status: bool,
        context: Context):

    while not queue.empty():
        package: DownloadPackageBody = queue.get_nowait()
        await download_package(package_name=package.packageName, version=package.version,
                               check_update_status=check_update_status, context=context)
        queue.task_done()


async def download_package(
        package_name: str,
        version: str,
        check_update_status: bool,
        context: Context):
    async def on_exit(ctx_exit):
        await ctx_exit.send(
            PackageEventResponse(packageName=package_name, version=version, event=Event.downloadDone)
        )
        if check_update_status:
            asyncio.create_task(check_update(local_package=TargetPackage.from_response(record), context=context))

    async with context.start(
            action=f"download package {package_name}#{version}",
            with_labels=[str(Label.PACKAGE_DOWNLOADING)],
            with_attributes={
                'packageName': package_name,
                'packageVersion': version
            },
            on_enter=lambda ctx_enter: ctx_enter.send(
                PackageEventResponse(packageName=package_name, version=version, event=Event.downloadStarted)
            ),
            on_exit=on_exit,
    ) as ctx:
        env = await context.get('env', YouwolEnvironment)
        remote_gtw = await RemoteClients.get_assets_gateway_client(context=ctx)
        default_drive = await env.get_default_drive(context=ctx)
        asset_id = encode_id(encode_id(package_name))

        await ctx.info(text=f"asset_id: {asset_id} queued for download")

        await create_asset_local(
            asset_id=asset_id,
            kind='package',
            default_owning_folder_id=default_drive.systemPackagesFolderId,
            get_raw_data=lambda _ctx: remote_gtw.cdn_get_package(
                library_name=package_name,
                version=version,
                headers=_ctx.headers()
            ),
            to_post_raw_data=lambda pack: {'file': pack},
            context=ctx
        )
        db = parse_json(env.pathsBook.local_cdn_docdb)
        versions = [d for d in db['documents'] if d['library_name'] == package_name]
        version = version if version != "latest" else max([p["version"] for p in versions])
        record = next(d for d in versions if d['library_id'] == f"{package_name}#{version}")
        response = DownloadedPackageResponse(
            packageName=package_name,
            version=version,
            versions=[d['version'] for d in versions],
            fingerprint=record['fingerprint']
        )
        await ctx.send(response)


async def get_version_info(version_data, env: YouwolEnvironment):

    cdn = LocalClients.get_cdn_client(env)
    version = version_data['version']
    entry_point = version_data['bundle']
    folder_path = '/'.join(entry_point.split('/')[:-1])
    folder_content, root_content = await asyncio.gather(
        cdn.get_explorer(library_id=encode_id(version_data['library_name']), version=version, folder_path=folder_path),
        cdn.get_explorer(library_id=encode_id(version_data['library_name']), version=version, folder_path="")
    )
    files_count = root_content['filesCount']
    entry_point_size = next((file['size'] for file in folder_content['files']
                             if file['name'] == entry_point.split('/')[-1]), None)
    return {"filesCount": files_count, "entryPointSize": entry_point_size or -1, "version": version}
