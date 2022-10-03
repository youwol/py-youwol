from fastapi import APIRouter

from starlette.requests import Request

from youwol.utils.utils_low_level import redirect_api_remote
from youwol_utils.context import Context

router = APIRouter()


@router.get("/{rest_of_path:path}",
            summary="return file content")
async def get(request: Request):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await redirect_api_remote(request=request, context=ctx)


@router.post("/{rest_of_path:path}",
            summary="return file content")
async def post(request: Request):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await redirect_api_remote(request=request, context=ctx)


@router.put("/{rest_of_path:path}",
            summary="return file content")
async def put(request: Request):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await redirect_api_remote(request=request, context=ctx)


@router.delete("/{rest_of_path:path}",
            summary="return file content")
async def delete(request: Request):

    async with Context.start_ep(
            request=request
    ) as ctx:
        return await redirect_api_remote(request=request, context=ctx)
