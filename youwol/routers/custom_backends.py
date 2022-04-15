from typing import List

from fastapi import APIRouter, FastAPI

from youwol_utils.context import Context
from youwol_utils.servers.fast_api import FastApiRouter

router = APIRouter()


async def install_routers(routers: List[FastApiRouter], ctx: Context):
    for r in routers:
        child_router = await r.router(ctx)
        router.include_router(router=child_router, prefix=r.base_path, tags=[])

    fastapi_app = await ctx.get('fastapi_app', FastAPI)
    fastapi_app.include_router(router, tags=[])
