import asyncio
from enum import Enum
from itertools import groupby
from typing import NamedTuple, List, Optional
from pydantic import BaseModel
from fastapi import HTTPException

from youwol.configuration.clients import RemoteClients
from youwol.configuration.youwol_configuration import Context
from youwol.models import Label
from youwol.utils_paths import parse_json
from youwol_utils import encode_id


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


class UpdateStatus(Enum):
    upToDate = 'upToDate'
    mismatch = 'mismatch'
    remoteAhead = "remoteAhead"
    localAhead = "localAhead"


class PackageVersionInfo(BaseModel):
    version: str
    fingerprint: str


class CheckUpdateResponse(BaseModel):
    packageName: str
    localVersionInfo: PackageVersionInfo
    remoteVersionInfo: PackageVersionInfo
    status: UpdateStatus


def get_latest_local_cdn_version(context: Context) -> List[TargetPackage]:

    db_path = parse_json(context.config.pathsBook.local_cdn_docdb)
    data = sorted(db_path['documents'], key=lambda d: d['library_name'])
    groups = [list(g) for _, g in groupby(data, key=lambda d: d['library_name'])]
    targets = [max(g, key=lambda d: int(d['version_number'])) for g in groups]

    return [TargetPackage.from_response(t) for t in targets]


async def check_update(queue: asyncio.Queue, context: Context):

    remote_gtw_client = await RemoteClients.get_assets_gateway_client(context=context)
    headers = {
        "authorization": context.request.headers.get("authorization")
    }
    while not queue.empty():
        local_package: TargetPackage = queue.get_nowait()
        response: Optional[CheckUpdateResponse] = None
        async with context.start(
                action=f"Check update for {local_package.library_name}",
                labels=[Label.INFO],
                succeeded_data=lambda _ctx: ('CheckUpdateResponse', response),
                with_attributes={
                    'event': 'check_update_pending',
                    'packageName': local_package.library_name,
                    'packageVersion': local_package.version,
                }) as ctx:
            package_id = encode_id(local_package.library_name)
            try:
                remote_package = await remote_gtw_client.cdn_get_versions(package_id=package_id, headers=headers)
            except HTTPException as e:
                if e.status_code == 404:
                    await ctx.info(text=f"{local_package.library_name} does not exist in remote")
                    queue.task_done()
                    return
                await ctx.error(text=f"Error occurred while checking {local_package.library_name}",
                                data={'detail': e.detail, "statusCode": e.status_code}
                                )
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
                localVersionInfo=PackageVersionInfo(version=local_package.version,
                                                    fingerprint=local_package.fingerprint),
                remoteVersionInfo=PackageVersionInfo(version=latest['version'], fingerprint=latest['fingerprint'])
            )
            queue.task_done()
