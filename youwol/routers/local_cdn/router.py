import asyncio
from typing import List

from fastapi import APIRouter
from starlette.requests import Request

from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.local_cdn.implementation import get_latest_local_cdn_version, check_updates_from_queue, \
    download_packages_from_queue
from youwol.routers.local_cdn.models import CheckUpdatesResponse, CheckUpdateResponse, DownloadPackagesBody
from youwol.web_socket import UserContextLogger
from youwol_utils.context import Context

router = APIRouter()


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
