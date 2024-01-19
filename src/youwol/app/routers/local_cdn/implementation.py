# standard library
import asyncio

from itertools import groupby

# typing
from typing import NamedTuple

# third parties
from fastapi import HTTPException

# Youwol application
from youwol.app.environment import LocalClients, RemoteClients, YouwolEnvironment
from youwol.app.routers.commons import Label
from youwol.app.routers.environment.download_assets.common import create_asset_local

# Youwol backends
from youwol.backends.cdn import (
    get_version_info_impl,
    library_model_from_doc,
    list_versions,
    to_package_id,
)
from youwol.backends.cdn.utils_indexing import get_version_number

# Youwol utilities
from youwol.utils import encode_id
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import Library
from youwol.utils.http_clients.cdn_backend.utils import resolve_version

# relative
from .models import (
    CheckUpdateResponse,
    DownloadedPackageResponse,
    DownloadPackageBody,
    Event,
    PackageEventResponse,
    PackageVersionInfo,
    UpdateStatus,
)


class TargetPackage(NamedTuple):
    library_name: str
    library_id: str
    version: str
    version_number: int
    fingerprint: str

    @staticmethod
    def from_response(d: Library):
        return TargetPackage(
            library_name=d.name,
            library_id=d.id,
            version=d.version,
            version_number=get_version_number(d.version),
            fingerprint=d.fingerprint,
        )


def get_latest_local_cdn_version(env: YouwolEnvironment) -> list[TargetPackage]:
    db_path = env.backends_configuration.cdn_backend.doc_db.data
    data = sorted(db_path["documents"], key=lambda d: d["library_name"])
    groups = [list(g) for _, g in groupby(data, key=lambda d: d["library_name"])]
    targets = [max(g, key=lambda d: int(d["version_number"])) for g in groups]
    targets = [library_model_from_doc(t) for t in targets]
    return [TargetPackage.from_response(t) for t in targets]


async def check_update(local_package: TargetPackage, context: Context):
    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
    remote_gtw_client = await RemoteClients.get_twin_assets_gateway_client(env)
    headers = {"authorization": context.headers().get("authorization")}
    name, version = local_package.library_name, local_package.version
    async with context.start(
        action=f"Check update for {local_package.library_name}",
        on_enter=lambda ctx_enter: ctx_enter.send(
            PackageEventResponse(
                packageName=name, version=version, event=Event.updateCheckStarted
            )
        ),
        on_exit=lambda ctx_exit: ctx_exit.send(
            PackageEventResponse(
                packageName=name, version=version, event=Event.updateCheckDone
            )
        ),
        with_attributes={
            "event": "check_update_pending",
            "packageName": name,
            "packageVersion": version,
        },
    ) as ctx:
        package_id = encode_id(local_package.library_name)

        try:
            remote_package = (
                await remote_gtw_client.get_cdn_backend_router().get_library_info(
                    library_id=package_id, headers=headers
                )
            )
        except HTTPException as e:
            if e.status_code == 404:
                await ctx.info(text=f"{name} does not exist in remote")
            raise e
        await ctx.info(
            text="Retrieved remote info", data={"remote_package": remote_package}
        )

        latest = remote_package["releases"][0]
        status = UpdateStatus.mismatch
        if latest["fingerprint"] == local_package.fingerprint:
            status = UpdateStatus.upToDate
        elif latest["version_number"] > local_package.version_number:
            status = UpdateStatus.remoteAhead
        elif latest["version_number"] < local_package.version_number:
            status = UpdateStatus.localAhead

        await ctx.info(text=f"Status: {str(status)}")
        response = CheckUpdateResponse(
            status=status,
            packageName=local_package.library_name,
            localVersionInfo=PackageVersionInfo(
                version=version, fingerprint=local_package.fingerprint
            ),
            remoteVersionInfo=PackageVersionInfo(
                version=latest["version"], fingerprint=latest["fingerprint"]
            ),
        )
        await ctx.send(response)
        return response


async def check_updates_from_queue(
    queue: asyncio.Queue, all_updates: list[CheckUpdateResponse], context: Context
):
    while not queue.empty():
        local_package: TargetPackage = queue.get_nowait()
        try:
            response = await check_update(local_package=local_package, context=context)
        except HTTPException as e:
            if e.status_code == 404:
                queue.task_done()
                return
            await context.error(
                text=f"Error occurred while checking {local_package.library_name}",
                data={"detail": e.detail, "statusCode": e.status_code},
            )
            raise e
        all_updates.append(response)
        queue.task_done()


async def download_packages_from_queue(
    queue: asyncio.Queue, check_update_status: bool, context: Context
):
    while not queue.empty():
        package: DownloadPackageBody = queue.get_nowait()
        await download_package(
            package_name=package.packageName,
            version=package.version,
            check_update_status=check_update_status,
            context=context,
        )
        queue.task_done()


async def download_package(
    package_name: str, version: str, check_update_status: bool, context: Context
):
    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)

    async def on_exit(ctx_exit):
        await ctx_exit.send(
            PackageEventResponse(
                packageName=package_name, version=version, event=Event.downloadDone
            )
        )
        if check_update_status and record is not None:
            asyncio.create_task(
                check_update(
                    local_package=TargetPackage.from_response(record), context=context
                )
            )

    async def sync_raw_data(
        asset_id: str, remote_gtw: AssetsGatewayClient, caller_context: Context
    ):
        async with caller_context.start(
            action="Sync. raw data of cdn-package",
            with_attributes={"asset_id": asset_id},
        ) as ctx:
            library_id = encode_id(package_name)
            resp = await remote_gtw.get_cdn_backend_router().download_library(
                library_id=library_id, version=version, headers=ctx.headers()
            )

            await LocalClients.get_cdn_client(env=env).publish(
                zip_content=resp, headers=ctx.headers()
            )

    async with context.start(
        action=f"download package {package_name}#{version}",
        with_labels=[str(Label.PACKAGE_DOWNLOADING)],
        with_attributes={"packageName": package_name, "packageVersion": version},
        on_enter=lambda ctx_enter: ctx_enter.send(
            PackageEventResponse(
                packageName=package_name, version=version, event=Event.downloadStarted
            )
        ),
        on_exit=on_exit,
    ) as ctx_download:
        record = None
        cdn_config = env.backends_configuration.cdn_backend
        await create_asset_local(
            asset_id=encode_id(encode_id(package_name)),
            kind="package",
            sync_raw_data=sync_raw_data,
            context=ctx_download,
        )
        info = await list_versions(
            name=package_name,
            max_results=int(1e6),
            context=ctx_download,
            configuration=cdn_config,
        )
        versions = info.versions
        version = await resolve_version(
            name=package_name, version=version, versions=versions, context=ctx_download
        )
        record = await get_version_info_impl(
            library_id=to_package_id(package_name),
            version=version,
            configuration=cdn_config,
            context=ctx_download,
        )
        response = DownloadedPackageResponse(
            packageName=package_name,
            version=version,
            versions=versions,
            fingerprint=record.fingerprint,
        )
        await ctx_download.send(response)


async def get_version_info(version_data, env: YouwolEnvironment, context: Context):
    cdn = LocalClients.get_cdn_client(env)
    version = version_data["version"]
    entry_point = version_data["bundle"]
    folder_path = "/".join(entry_point.split("/")[:-1])
    folder_content, root_content = await asyncio.gather(
        cdn.get_explorer(
            library_id=encode_id(version_data["library_name"]),
            version=version,
            folder_path=folder_path,
            headers=context.headers(),
        ),
        cdn.get_explorer(
            library_id=encode_id(version_data["library_name"]),
            version=version,
            folder_path="",
            headers=context.headers(),
        ),
    )
    files_count = root_content["filesCount"]
    entry_point_size = next(
        (
            file["size"]
            for file in folder_content["files"]
            if file["name"] == entry_point.split("/")[-1]
        ),
        None,
    )
    return {
        "filesCount": files_count,
        "entryPointSize": entry_point_size or -1,
        "version": version,
    }
