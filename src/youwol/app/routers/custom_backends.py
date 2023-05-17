# standard library
import inspect

# typing
from typing import Awaitable, Callable, List, Union, cast

# third parties
from fastapi import APIRouter, FastAPI

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.servers.fast_api import FastApiRouter

router = APIRouter()


async def install_routers(routers: List[FastApiRouter], ctx: Context):
    for r in routers:
        type_fct = Callable[[Context], Union[APIRouter, Awaitable[APIRouter]]]
        # Not sure why the typing.cast below is required
        # r.router is of type Union[APIRouter, type_fct] (see FastApiRouter)
        child_router = (
            r.router
            if isinstance(r.router, APIRouter)
            else cast(r.router, type_fct)(ctx)
        )
        if inspect.isawaitable(child_router):
            child_router = await child_router
        router.include_router(router=child_router, prefix=r.base_path, tags=[])

    fastapi_app = await ctx.get("fastapi_app", FastAPI)
    fastapi_app.include_router(router, tags=[])
