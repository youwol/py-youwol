import asyncio
from typing import Mapping

import aiohttp
from aiohttp import ClientConnectorError
from fastapi import HTTPException, Depends
from starlette.requests import Request
from starlette.responses import Response

from starlette.datastructures import Headers

from routers.backends.utils import get_all_backends
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.context import Context
from youwol.web_socket import WebSocketsCache

#from routers.api import redirect_get_api, redirect_post_api, redirect_put_api, redirect_delete_api, redirect_get


async def get_headers(context: Context) -> Headers:
    with_headers = await context.config.userConfig.general.localGateway.with_headers(context)
    return Headers(headers={**context.request.headers, **with_headers})


async def get_backend_url(service_name: str, path: str, context: Context) -> str:
    backends = await get_all_backends(context)
    backend = next(backend for backend in backends if backend.info.name == service_name)
    end_point = backend.pipeline.serve.end_point(path, backend.target, context)
    return f"http://localhost:{backend.info.port}/{end_point}"


async def redirect_api_remote(request: Request, redirect_url: str = None):

    new_path = redirect_url if redirect_url else f'https://gc.platform.youwol.com{request.url.path}'
    # One of the header item leads to a server error ... for now only provide authorization
    # headers = {k: v for k, v in request.headers.items()}
    headers = {"Authorization": request.headers.get("authorization")}

    if request.method == 'GET':
        resp = await redirect_get(request, new_path, headers)
        return resp

    return None


async def redirect_api_local(request: Request, service_name: str, rest_of_path: str, config: any):

    """
    service_name = base_path.split('api/')[1]
    rest_of_path = request.url.path.split(f'/{service_name}/')[1]
    """
    if request.method == 'GET':
        return await redirect_get_api(request, service_name, rest_of_path, config)
    if request.method == 'POST':
        return await redirect_post_api(request, service_name, rest_of_path, config)
    if request.method == 'PUT':
        return await redirect_put_api(request, service_name, rest_of_path, config)
    if request.method == 'DELETE':
        return await redirect_delete_api(request, service_name, rest_of_path, config)
    pass


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
