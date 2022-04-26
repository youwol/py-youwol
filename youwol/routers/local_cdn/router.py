import asyncio
import itertools
from typing import List

from fastapi import APIRouter
from starlette.requests import Request

from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.local_cdn.implementation import get_latest_local_cdn_version, check_updates_from_queue, \
    download_packages_from_queue, get_version_info
from youwol.routers.local_cdn.models import CheckUpdatesResponse, CheckUpdateResponse, DownloadPackagesBody, \
    ResetCdnBody, PackageEvent, Event, CdnStatusResponse, CdnPackage, CdnVersion, CdnPackageResponse
from youwol.web_socket import UserContextLogger
from youwol_utils import decode_id, encode_id
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json

router = APIRouter()


@router.get("/status",
            summary="Provides description of available updates",
            response_model=CdnStatusResponse
            )
async def status(request: Request):
    async with Context.from_request(request).start(
            action="CDN status",
            with_attributes={'topic': 'cdn'},
            with_loggers=[UserContextLogger()]
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
            with_attributes={'topic': 'cdn', 'packageId': package_id},
            with_loggers=[UserContextLogger()]
    ) as ctx:  # type: Context
        package_name = decode_id(package_id)
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        cdn_docs = parse_json(env.pathsBook.local_cdn_docdb)["documents"]
        versions = [d for d in cdn_docs if d["library_name"] == package_name]
        response = CdnPackageResponse(
            name=package_name,
            id=package_id,
            versions=[CdnVersion(**get_version_info(version, env)) for version in versions]
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
            with_loggers=[UserContextLogger()]
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
            with_loggers=[UserContextLogger()]
    ) as ctx:
        await ctx.info(text=f"Proceed to {len(body.packages)} packages download", data=body)
        for package in body.packages:
            queue.put_nowait(package)

        tasks = [asyncio.create_task(download_packages_from_queue(queue=queue,
                                                                  check_update_status=body.checkUpdateStatus,
                                                                  context=ctx))
                 for _ in range(5)]

        await asyncio.gather(queue.join(), *tasks)
