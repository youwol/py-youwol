# third parties
from fastapi import APIRouter
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.utils_requests import redirect_request

router = APIRouter()


async def redirect_api_remote(request: Request, context: Context):
    async with context.start(action="redirect API in remote") as ctx:
        env = await context.get("env", YouwolEnvironment)
        redirect_base_path = f"https://{env.get_remote_info().host}/api"
        black_list = ["host"]
        headers = {
            **{k: v for k, v in request.headers.items() if k not in black_list},
            **ctx.headers(),
        }

        return await redirect_request(
            incoming_request=request,
            origin_base_path="/api",
            destination_base_path=redirect_base_path,
            headers=headers,
        )


@router.get("/{rest_of_path:path}", summary="return file content")
async def get(request: Request):
    async with Context.start_ep(request=request) as ctx:
        return await redirect_api_remote(request=request, context=ctx)


@router.post("/{rest_of_path:path}", summary="return file content")
async def post(request: Request):
    async with Context.start_ep(request=request) as ctx:
        return await redirect_api_remote(request=request, context=ctx)


@router.put("/{rest_of_path:path}", summary="return file content")
async def put(request: Request):
    async with Context.start_ep(request=request) as ctx:
        return await redirect_api_remote(request=request, context=ctx)


@router.delete("/{rest_of_path:path}", summary="return file content")
async def delete(request: Request):
    async with Context.start_ep(request=request) as ctx:
        return await redirect_api_remote(request=request, context=ctx)
