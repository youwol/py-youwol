import asyncio
import itertools
import shutil
from typing import List

from fastapi import APIRouter
from starlette.requests import Request

from youwol.environment.clients import LocalClients
from youwol.environment.projects_loader import ProjectLoader
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.local_cdn.implementation import get_latest_local_cdn_version, check_updates_from_queue, \
    download_packages_from_queue, get_version_info
from youwol.routers.local_cdn.models import CheckUpdatesResponse, CheckUpdateResponse, DownloadPackagesBody, \
    ResetCdnBody, PackageEventResponse, Event, CdnStatusResponse, CdnPackage, CdnVersion, CdnPackageResponse, cdn_topic, \
    ResetCdnResponse, HardResetCdnResponse, HardResetDbStatus
from youwol.web_socket import LogsStreamer
from youwol_utils import decode_id, encode_id
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json, write_json

router = APIRouter()


@router.get("/status",
            summary="Provides description of available packages",
            response_model=CdnStatusResponse
            )
async def status(request: Request):
    async with Context.from_request(request).start(
            action="CDN status",
            with_attributes={'topic': cdn_topic},
            with_reporters=[LogsStreamer()]
    ) as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_docs = parse_json(env.pathsBook.local_cdn_docdb)["documents"]
        cdn_sorted = sorted(cdn_docs, key=lambda d: d['library_name'])
        grouped = itertools.groupby(cdn_sorted, key=lambda d: d['library_name'])
        packages = [CdnPackage(
            name=name,
            id=encode_id(name),
            versions=[CdnVersion(**get_version_info(version, env)) for version in versions]
        ) for name, versions in grouped]
        response = CdnStatusResponse(packages=packages)
        await ctx.send(response)
        return response


@router.get("/packages/{package_id}",
            summary="Provides description of available updates",
            response_model=CdnPackageResponse
            )
async def package_info(request: Request, package_id: str):
    async with Context.from_request(request).start(
            action="package info",
            with_attributes={'topic': cdn_topic, 'packageId': package_id},
            with_reporters=[LogsStreamer()]
    ) as ctx:  # type: Context
        package_name = decode_id(package_id)
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_docs = parse_json(env.pathsBook.local_cdn_docdb)["documents"]
        versions = [d for d in cdn_docs if d["library_name"] == package_name]
        versions_info = await asyncio.gather(*[get_version_info(version, env) for version in versions])
        response = CdnPackageResponse(
            name=package_name,
            id=package_id,
            versions=[CdnVersion(**version_info) for version_info in versions_info]
        )
        await ctx.send(response)
        return response


@router.get("/collect-updates",
            summary="Provides description of available updates",
            response_model=CheckUpdatesResponse
            )
async def collect_updates(
        request: Request
        ):

    queue = asyncio.Queue()
    async with Context.from_request(request).start(
            action="collect available updates",
            with_attributes={'topic': 'updatesCdn'},
            with_reporters=[LogsStreamer()]
    ) as ctx:

        env = await ctx.get('env', YouwolEnvironment)
        local_packages_latest = get_latest_local_cdn_version(env)
        await ctx.info(text="local latest version of cdn packages retrieved",
                       data={'packages': {f"{p.library_name}#{p.version}": p for p in local_packages_latest}})
        for package in local_packages_latest:
            queue.put_nowait(package)
        updates: List[CheckUpdateResponse] = []
        tasks = [asyncio.create_task(check_updates_from_queue(queue=queue, all_updates=updates, context=ctx))
                 for _ in range(5)]

        await asyncio.gather(queue.join(), *tasks)
        response = CheckUpdatesResponse(
            updates=updates
        )
        await ctx.send(response)
        return response


@router.post("/download",
             summary="download"
             )
async def download(
        request: Request,
        body: DownloadPackagesBody
        ):

    queue = asyncio.Queue()

    async with Context.from_request(request).start(
            action="download packages",
            with_attributes={'topic': 'updatesCdn'},
            with_reporters=[LogsStreamer()]
    ) as ctx:
        await ctx.info(text=f"Proceed to {len(body.packages)} packages download", data=body)
        for package in body.packages:
            queue.put_nowait(package)

        tasks = [asyncio.create_task(download_packages_from_queue(queue=queue,
                                                                  check_update_status=body.checkUpdateStatus,
                                                                  context=ctx))
                 for _ in range(5)]

        await asyncio.gather(queue.join(), *tasks)


@router.post("/reset",
             response_model=ResetCdnResponse,
             summary="reset local CDN"
             )
async def smooth_reset(
        request: Request,
        body: ResetCdnBody
):
    async with Context.start_ep(
            request=request,
            action="reset CDN",
            with_attributes={'topic': 'updatesCdn'},
            with_reporters=[LogsStreamer()]
    ) as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        packages = [p for p in parse_json(env.pathsBook.local_assets_entities_docdb)['documents']
                    if p['kind'] == 'package']
        await ctx.info(f"Found a total of {len(packages)} packages",
                       data={"packages": [p['name'] for p in packages]})
        if body.keepProjectPackages:
            projects = [p.name for p in await ProjectLoader.get_projects(env, ctx)]
            packages = [p for p in packages if p['name'] not in projects]
            await ctx.info(f"Filter out packages from local projects",
                           data={"packages": [p['name'] for p in packages]})

        cdn_client = LocalClients.get_gtw_cdn_client(env)
        for package in packages:
            info = await cdn_client.get_library_info(library_id=package['related_id'], headers=ctx.headers())
            for version in info['versions']:
                await ctx.send(
                    PackageEventResponse(packageName=package['name'], version=version, event=Event.updateCheckStarted)
                )

            await cdn_client.delete_library(library_id=package['related_id'], params={'purge': "true"},
                                            headers=ctx.headers())
        await status(request=request)
        return ResetCdnResponse(deletedPackages=[p['name'] for p in packages])


@router.post("/hard-reset",
             response_model=HardResetCdnResponse,
             summary="reset local CDN"
             )
async def hard_reset(
        request: Request
):
    async with Context.start_ep(
            request=request,
            action="reset CDN",
            with_attributes={'topic': 'updatesCdn'},
            with_reporters=[LogsStreamer()]
    ) as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        packages = [p for p in parse_json(env.pathsBook.local_cdn_docdb)['documents']]
        asset_ids_to_delete = [encode_id(encode_id(p["library_name"])) for p in packages]

        await ctx.info(f"Found a total of {len(packages)} packages to remove",
                       data={"packages": [p['library_name'] for p in packages]})
        assets_entities = parse_json(env.pathsBook.local_assets_entities_docdb)['documents']
        assets_entities_remaining = [p for p in assets_entities if p['asset_id'] not in asset_ids_to_delete]

        assets_access = parse_json(env.pathsBook.local_assets_access_docdb)['documents']
        assets_access_remaining = [p for p in assets_access if p['asset_id'] not in asset_ids_to_delete]

        treedb_items = parse_json(env.pathsBook.local_treedb_items_docdb)['documents']
        treedb_items_remaining = [p for p in treedb_items if p['related_id'] not in asset_ids_to_delete]

        treedb_deleted = parse_json(env.pathsBook.local_treedb_deleted_docdb)['documents']
        treedb_deleted_remaining = [p for p in treedb_items if p['related_id'] not in asset_ids_to_delete]

        resp = HardResetCdnResponse(
            cdnLibraries=HardResetDbStatus(
                originalCount=len(packages),
                remainingCount=0
            ),
            assetEntities=HardResetDbStatus(
                originalCount=len(assets_entities),
                remainingCount=len(assets_entities_remaining)
            ),
            assetAccess=HardResetDbStatus(
                originalCount=len(assets_access),
                remainingCount=len(assets_access_remaining)
            ),
            treedbItems=HardResetDbStatus(
                originalCount=len(treedb_items),
                remainingCount=len(treedb_items_remaining)
            ),
            treedbDeleted=HardResetDbStatus(
                originalCount=len(treedb_deleted),
                remainingCount=len(treedb_deleted_remaining)
            )
        )
        write_json({"documents": []}, env.pathsBook.local_cdn_docdb)
        write_json({"documents": assets_entities_remaining}, env.pathsBook.local_assets_entities_docdb)
        write_json({"documents": assets_access_remaining}, env.pathsBook.local_assets_access_docdb)
        write_json({"documents": treedb_items_remaining}, env.pathsBook.local_treedb_items_docdb)
        write_json({"documents": treedb_deleted_remaining}, env.pathsBook.local_treedb_deleted_docdb)

        shutil.rmtree(env.pathsBook.local_cdn_storage, ignore_errors=True)
        await status(request=request)

        return resp
