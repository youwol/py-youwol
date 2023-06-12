# standard library
import asyncio
import itertools
import shutil

# typing
from typing import List

# third parties
from fastapi import APIRouter
from starlette.requests import Request

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.projects.projects_loader import ProjectLoader
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import decode_id, encode_id
from youwol.utils.context import Context

# relative
from .implementation import (
    check_updates_from_queue,
    download_packages_from_queue,
    get_latest_local_cdn_version,
    get_version_info,
)
from .models import (
    CdnPackageLight,
    CdnPackageResponse,
    CdnStatusResponse,
    CdnVersion,
    CdnVersionLight,
    CheckUpdateResponse,
    CheckUpdatesResponse,
    DownloadPackagesBody,
    Event,
    HardResetCdnResponse,
    HardResetDbStatus,
    PackageEventResponse,
    ResetCdnBody,
    ResetCdnResponse,
    cdn_topic,
)

router = APIRouter()


@router.get(
    "/status",
    summary="Provides description of available packages",
    response_model=CdnStatusResponse,
)
async def status(request: Request):
    async with Context.from_request(request).start(
        action="CDN status",
        with_attributes={"topic": cdn_topic},
        with_reporters=[LogsStreamer()],
    ) as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_docs = env.backends_configuration.cdn_backend.doc_db.data["documents"]
        cdn_sorted = sorted(cdn_docs, key=lambda d: d["library_name"])
        grouped = itertools.groupby(cdn_sorted, key=lambda d: d["library_name"])

        packages = [
            CdnPackageLight(
                name=name,
                id=encode_id(name),
                versions=[
                    CdnVersionLight(version=version_data["version"])
                    for version_data in versions
                ],
            )
            for name, versions in grouped
        ]
        response = CdnStatusResponse(packages=packages)
        await ctx.send(response)
        return response


@router.get(
    "/packages/{package_id}",
    summary="Provides description of available updates",
    response_model=CdnPackageResponse,
)
async def package_info(request: Request, package_id: str):
    async with Context.from_request(request).start(
        action="package info",
        with_attributes={"topic": cdn_topic, "packageId": package_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:  # type: Context
        package_name = decode_id(package_id)
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_docs = env.backends_configuration.cdn_backend.doc_db.data["documents"]
        versions = [d for d in cdn_docs if d["library_name"] == package_name]
        versions_info = await asyncio.gather(
            *[
                get_version_info(version_data=version, env=env, context=ctx)
                for version in versions
            ]
        )
        response = CdnPackageResponse(
            name=package_name,
            id=package_id,
            versions=[CdnVersion(**version_info) for version_info in versions_info],
        )
        await ctx.send(response)
        return response


@router.get(
    "/collect-updates",
    summary="Provides description of available updates",
    response_model=CheckUpdatesResponse,
)
async def collect_updates(request: Request):
    queue = asyncio.Queue()
    async with Context.from_request(request).start(
        action="collect available updates",
        with_attributes={"topic": "updatesCdn"},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        local_packages_latest = get_latest_local_cdn_version(env)
        await ctx.info(
            text="local latest version of cdn packages retrieved",
            data={
                "packages": {
                    f"{p.library_name}#{p.version}": p for p in local_packages_latest
                }
            },
        )
        for package in local_packages_latest:
            queue.put_nowait(package)
        updates: List[CheckUpdateResponse] = []
        tasks = [
            asyncio.create_task(
                check_updates_from_queue(queue=queue, all_updates=updates, context=ctx)
            )
            for _ in range(5)
        ]

        await asyncio.gather(queue.join(), *tasks)
        response = CheckUpdatesResponse(updates=updates)
        await ctx.send(response)
        return response


@router.post("/download", summary="download")
async def download(request: Request, body: DownloadPackagesBody):
    queue = asyncio.Queue()

    async with Context.from_request(request).start(
        action="download packages",
        with_attributes={"topic": "updatesCdn"},
        with_reporters=[LogsStreamer()],
        muted_http_errors={404},
    ) as ctx:
        await ctx.info(
            text=f"Proceed to {len(body.packages)} packages download", data=body
        )
        for package in body.packages:
            queue.put_nowait(package)

        tasks = [
            asyncio.create_task(
                download_packages_from_queue(
                    queue=queue, check_update_status=body.checkUpdateStatus, context=ctx
                )
            )
            for _ in range(5)
        ]

        await asyncio.gather(queue.join(), *tasks)


@router.post("/reset", response_model=ResetCdnResponse, summary="reset local CDN")
async def smooth_reset(request: Request, body: ResetCdnBody):
    async with Context.start_ep(
        request=request,
        action="reset CDN",
        with_attributes={"topic": "updatesCdn"},
        with_reporters=[LogsStreamer()],
    ) as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        entities = env.backends_configuration.assets_backend.doc_db_asset.data
        packages = [p for p in entities["documents"] if p["kind"] == "package"]
        await ctx.info(
            f"Found a total of {len(packages)} packages",
            data={"packages": [p["name"] for p in packages]},
        )
        if body.keepProjectPackages:
            projects = [p.name for p in await ProjectLoader.get_cached_projects()]
            packages = [p for p in packages if p["name"] not in projects]
            await ctx.info(
                "Filter out packages from local projects",
                data={"packages": [p["name"] for p in packages]},
            )

        # The current user may not have the permissions to delete the package as it can belong to a 'forbidden' group
        # for him (still, we want to proceed as it is the local version of YouWol and such things are expected).
        # To skip permissions checks, we use 'LocalClients.get_cdn_client' and not 'LocalClients.get_gtw_cdn_client'.
        # Because of this, the 'asset' must be explicitly deleted using 'assets_client.delete_asset'.
        cdn_client = LocalClients.get_cdn_client(env)
        assets_client = LocalClients.get_assets_client(env)
        for package in packages:
            info = await cdn_client.get_library_info(
                library_id=package["related_id"], headers=ctx.headers()
            )
            for version in info["versions"]:
                await ctx.send(
                    PackageEventResponse(
                        packageName=package["name"],
                        version=version,
                        event=Event.updateCheckStarted,
                    )
                )

            await cdn_client.delete_library(
                library_id=package["related_id"],
                params={"purge": "true"},
                headers=ctx.headers(),
            )
            await assets_client.delete_asset(
                asset_id=package["asset_id"], headers=ctx.headers()
            )

        await status(request=request)
        return ResetCdnResponse(deletedPackages=[p["name"] for p in packages])


@router.post(
    "/hard-reset", response_model=HardResetCdnResponse, summary="reset local CDN"
)
async def hard_reset(request: Request):
    async with Context.start_ep(
        request=request,
        action="reset CDN",
        with_attributes={"topic": "updatesCdn"},
        with_reporters=[LogsStreamer()],
    ) as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_packages = env.backends_configuration.cdn_backend.doc_db.data
        packages = list(cdn_packages["documents"])
        asset_ids_to_delete = [
            encode_id(encode_id(p["library_name"])) for p in packages
        ]

        await ctx.info(
            f"Found a total of {len(packages)} packages to remove",
            data={"packages": [p["library_name"] for p in packages]},
        )
        assets_entities = env.backends_configuration.assets_backend.doc_db_asset.data
        assets_entities_remaining = [
            p
            for p in assets_entities["documents"]
            if p["asset_id"] not in asset_ids_to_delete
        ]

        assets_access = (
            env.backends_configuration.assets_backend.doc_db_access_policy.data
        )
        assets_access_remaining = [
            p
            for p in assets_access["documents"]
            if p["asset_id"] not in asset_ids_to_delete
        ]

        treedb_items = env.backends_configuration.tree_db_backend.doc_dbs.items_db.data
        treedb_items_remaining = [
            p
            for p in treedb_items["documents"]
            if p["related_id"] not in asset_ids_to_delete
        ]

        treedb_deleted = (
            env.backends_configuration.tree_db_backend.doc_dbs.deleted_db.data
        )
        treedb_deleted_remaining = [
            p
            for p in treedb_items["documents"]
            if p["related_id"] not in asset_ids_to_delete
        ]

        resp = HardResetCdnResponse(
            cdnLibraries=HardResetDbStatus(
                originalCount=len(packages), remainingCount=0
            ),
            assetEntities=HardResetDbStatus(
                originalCount=len(assets_entities),
                remainingCount=len(assets_entities_remaining),
            ),
            assetAccess=HardResetDbStatus(
                originalCount=len(assets_access),
                remainingCount=len(assets_access_remaining),
            ),
            treedbItems=HardResetDbStatus(
                originalCount=len(treedb_items),
                remainingCount=len(treedb_items_remaining),
            ),
            treedbDeleted=HardResetDbStatus(
                originalCount=len(treedb_deleted),
                remainingCount=len(treedb_deleted_remaining),
            ),
        )
        cdn_packages["documents"] = []
        assets_entities["documents"] = assets_entities_remaining
        assets_access["documents"] = assets_access_remaining
        treedb_items["documents"] = treedb_items_remaining
        treedb_deleted["documents"] = treedb_deleted_remaining

        shutil.rmtree(env.pathsBook.local_cdn_storage, ignore_errors=True)
        await status(request=request)

        return resp
