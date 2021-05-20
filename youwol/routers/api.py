import asyncio
from typing import Optional, Mapping

import aiohttp
from aiohttp import ClientConnectorError
from fastapi import APIRouter, HTTPException, Depends, Form
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response

from youwol.routers.environment.router import login as login_env
from youwol.routers.environment.models import LoginBody
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.context import Context
from youwol.routers.backends.utils import get_all_backends
from youwol.web_socket import WebSocketsCache

import youwol.services.backs.cdn.root_paths as cdn
import youwol.services.backs.treedb.root_paths as treedb
import youwol.services.backs.assets.root_paths as assets
import youwol.services.backs.flux.root_paths as flux
import youwol.services.backs.assets_gateway.root_paths as assets_gateway


router = APIRouter()
cached_headers = None


router.include_router(cdn.router, prefix="/cdn-backend", tags=["cdn"])
router.include_router(treedb.router, prefix="/treedb-backend", tags=["treedb"])
router.include_router(assets.router, prefix="/assets-backend", tags=["assets"])
router.include_router(flux.router, prefix="/flux-backend", tags=["assets"])
router.include_router(assets_gateway.router, prefix="/assets-gateway", tags=["assets-gateway"])


async def get_headers(context: Context) -> Headers:
    with_headers = await context.config.userConfig.general.localGateway.with_headers(context)
    return Headers(headers={**context.request.headers, **with_headers})


async def get_backend_url(service_name: str, path: str, context: Context) -> str:
    backends = await get_all_backends(context)
    backend = next(backend for backend in backends if backend.info.name == service_name)
    return f"http://localhost:{backend.info.port}/{path}"


@router.get("/authorization/user-info",
            summary="retrieve user info")
async def get_user_info(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    user_info = config.get_user_info()
    return {
        "sub": user_info.id,
        "email_verified": True,
        "name": user_info.name,
        "preferred_username": user_info.name,
        "memberof": user_info.memberOf,
        "email": user_info.email,
        }


@router.post("/authorization/login",
             summary="login with as new user")
async def login(
        request: Request,
        username: Optional[str] = Form(None),
        config: YouwolConfiguration = Depends(yw_config)
        ):
    """
    this end point should be defined in the user configuration file as it is usually intended
    to mock some auth service fro which we don't know the format of the request
    """
    resp = await login_env(request=request, body=LoginBody(email=username), config=config)
    return {"access_token": f"access_token_{resp.email}"}


async def redirect_get(
        request: Request,
        new_url: str,
        headers: Mapping[str, str]
        ):
    params = request.query_params
    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False),
            auto_decompress=False) as session:

        async with await session.get(url=new_url, params=params, headers=headers) as resp:
            # if this is a GET request to assets-gateway we don't want caching as in local we can update assets
            headers_resp = {
                **{k: v for k, v in resp.headers.items()}
                }

            content = await resp.read()
            return Response(status_code=resp.status, content=content, headers=headers_resp)


@router.get("/{service_name}/{rest_of_path:path}")
async def redirect_get_api(
        request: Request,
        service_name: str,
        rest_of_path: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(
        web_socket=WebSocketsCache.api_gateway,
        config=config,
        request=request
        )
    try:
        url, headers = await asyncio.gather(
            get_backend_url(service_name, rest_of_path, context),
            get_headers(context)
            )
    except (StopIteration, RuntimeError) as e:
        raise Exception(f"Can not find url of service {service_name} (from url: {service_name}/{rest_of_path})," +
                        " is it in your config file?")

    try:
        return await redirect_get(request=request, new_url=url, headers=headers)
    except ClientConnectorError:
        raise HTTPException(status_code=500, detail=f"Can not connect to {service_name}")


@router.post("/{service_name}/{rest_of_path:path}")
async def redirect_post_api(
        request: Request,
        service_name: str,
        rest_of_path: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(
        web_socket=WebSocketsCache.api_gateway,
        config=config,
        request=request
        )

    url = await get_backend_url(service_name, rest_of_path, context)

    data = await request.body()
    headers = await get_headers(context)
    params = request.query_params

    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False),
            auto_decompress=False) as session:

        async with await session.post(url=url, data=data, params=params, headers=headers) as resp:
            headers_resp = {k: v for k, v in resp.headers.items()}
            content = await resp.read()
            return Response(status_code=resp.status, content=content, headers=headers_resp)


@router.put("/{service_name}/{rest_of_path:path}")
async def redirect_put_api(
        request: Request,
        service_name: str,
        rest_of_path: str,
        config: YouwolConfiguration = Depends(yw_config)):

    context = Context(
        web_socket=WebSocketsCache.api_gateway,
        config=config,
        request=request
        )
    url = await get_backend_url(service_name, rest_of_path, context)

    data = await request.body()
    headers = await get_headers(context)
    params = request.query_params

    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False),
            auto_decompress=False) as session:

        async with await session.put(url=url, data=data, params=params, headers=headers) as resp:
            headers_resp = {k: v for k, v in resp.headers.items()}
            content = await resp.read()
            return Response(status_code=resp.status, content=content, headers=headers_resp)


@router.delete("/{service_name}/{rest_of_path:path}")
async def redirect_delete_api(
        request: Request,
        service_name: str,
        rest_of_path: str,
        config: YouwolConfiguration = Depends(yw_config)):

    context = Context(
        web_socket=WebSocketsCache.api_gateway,
        config=config,
        request=request
        )

    url = await get_backend_url(service_name, rest_of_path, context)
    params = request.query_params

    data = await request.body()
    headers = await get_headers(context)

    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False),
            auto_decompress=False) as session:

        async with await session.delete(url=url, data=data,  params=params, headers=headers) as resp:
            headers_resp = {k: v for k, v in resp.headers.items()}
            content = await resp.read()
            return Response(status_code=resp.status, content=content, headers=headers_resp)
