# standard library
import itertools

# third parties
from fastapi import APIRouter, Depends
from starlette.requests import Request

# Youwol utilities
from youwol.utils.context import Context

# relative
from .configurations import Configuration, get_configuration

router = APIRouter(tags=["custom-backend"])
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "custom backend serving"}


@router.get(
    "/config",
    response_model=Configuration,
    summary="return the service's configuration",
)
async def config(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        await ctx.info(text="Just return the configuration")
        return configuration
