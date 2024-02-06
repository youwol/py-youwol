# standard library
import inspect

# third parties
from fastapi import APIRouter, FastAPI

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.servers.fast_api import FastApiRouter

router = APIRouter()


async def install_routers(routers: list[FastApiRouter], ctx: Context):
    for r in routers:
        child_router = r.router
        if inspect.isawaitable(child_router):
            child_router = await child_router
        router.include_router(router=child_router, prefix=r.base_path, tags=[])

    fastapi_app = await ctx.get("fastapi_app", FastAPI)
    fastapi_app.include_router(router, tags=[])
