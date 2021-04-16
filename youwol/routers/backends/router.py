import asyncio
import itertools
import os
from asyncio import sleep

from fastapi import APIRouter, WebSocket, Depends, HTTPException
from starlette.requests import Request

from youwol.configuration.user_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config, YouwolConfigurationFactory
from youwol.configurations import configuration
from youwol.context import Context
from youwol.models import Action
from youwol.routers.api import redirect_get_api
from youwol.routers.backends.utils import get_all_backends, BackEnd, get_status, get_port_number
from youwol.routers.backends.models import StatusResponse, AllStatusResponse
from youwol.routers.backends.utils import ping
from youwol.routers.commons import (
    SkeletonsResponse, PostSkeletonBody, list_skeletons,
    create_skeleton,
    )
from youwol.web_socket import WebSocketsCache

from youwol.routers.environment.router import status as env_status

router = APIRouter()
flatten = itertools.chain.from_iterable


async def is_serving(backend: BackEnd, context: Context):
    health = backend.pipeline.serve.health
    try:
        api_status = await redirect_get_api(
            request=context.request,
            service_name=backend.info.name,
            rest_of_path=health[1:],
            config=context.config
            )
    except HTTPException:
        return False

    return api_status.status_code == 200


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.backends = ws
    await ws.send_json({})
    while True:
        _ = await ws.receive_text()


@router.get("/status",
            response_model=AllStatusResponse,
            summary="status")
async def status(request: Request, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(request=request, config=config, web_socket=WebSocketsCache.backends)
    all_backs = await get_all_backends(context=context)
    py_yw_config = configuration

    dev_servers = await asyncio.gather(*[is_serving(backend, context) for backend in all_backs])
    all_status = await asyncio.gather(*[get_status(backend, context) for backend in all_backs])

    health_urls = [f"http://localhost:{py_yw_config.http_port}/api/{backend.info.name}{backend.pipeline.serve.health}"
                   for backend in all_backs]
    healths = await asyncio.gather(*[ping(url) for url in health_urls])
    all_status = [StatusResponse(name=backend.info.name,
                                 assetId=backend.assetId,
                                 health=health,
                                 url=f'/api/{backend.info.name}',
                                 devServer=dev_server,
                                 openApi=backend.pipeline.serve.open_api(backend, context),
                                 installStatus=steps.install_status.name)
                  for backend, health, dev_server, steps in zip(all_backs, healths, dev_servers, all_status)]

    resp = AllStatusResponse(status=all_status)
    WebSocketsCache.backends and await WebSocketsCache.backends.send_json({
        **{"type": "Status"},
        **resp.dict()
        })

    return AllStatusResponse(status=all_status)


@router.get("/skeletons",
            response_model=SkeletonsResponse,
            summary="list the available skeletons")
async def skeletons(
        config: YouwolConfiguration = Depends(yw_config)
        ):

    resp = await list_skeletons(pipelines=config.userConfig.backends.pipelines)
    return resp


@router.post("/skeletons/{pipeline}",
             summary="create skeleton")
async def post_skeletons(
        request: Request,
        pipeline: str,
        body: PostSkeletonBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(request=request, config=config, web_socket=WebSocketsCache.backends)
    pipeline = config.userConfig.backends.pipelines[pipeline]
    skeleton = await create_skeleton(body=body, pipeline=pipeline, context=context)
    await YouwolConfigurationFactory.reload()
    new_conf = await yw_config()
    await env_status(request, new_conf)
    return skeleton


@router.post("/{asset_id}/install",
             summary="install")
async def install(
        request: Request,
        asset_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(request=request, config=config, web_socket=WebSocketsCache.backends)
    all_backs = await get_all_backends(context=context)
    back = next(back for back in all_backs if back.assetId == asset_id)

    async with context.with_target(back.info.name).start(Action.INSTALL) as ctx:

        await back.pipeline.install.exe(resource=back, context=ctx)

    await YouwolConfigurationFactory.reload()
    new_conf = await yw_config()
    await env_status(request, new_conf)


@router.post("/{asset_id}/start", summary="execute action")
async def start(request: Request, asset_id: str, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(request=request, config=config, web_socket=WebSocketsCache.backends)
    all_backs = await get_all_backends(context=context)
    back = next(back for back in all_backs if back.assetId == asset_id)
    asyncio.run_coroutine_threadsafe(
        back.pipeline.serve.exe(back, context.with_target(back.assetId)),
        asyncio.get_event_loop())

    health_url = f"http://localhost:{config.http_port}/api/{back.info.name}{back.pipeline.serve.health}"

    for i in range(10):
        await sleep(0.2)
        resp = await ping(health_url)
        if resp:
            break
    await status(request=request, config=config)

    return {'action': 'start', 'target': asset_id}


@router.post("/{asset_id}/stop", summary="execute action")
async def stop(request: Request, asset_id: str, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(request=request, config=config, web_socket=WebSocketsCache.backends)
    all_backs = await get_all_backends(context=context)
    back = next(back for back in all_backs if back.assetId == asset_id)
    os.system("kill -9 `lsof -t -i:{}`".format(get_port_number(back.target)))
    await status(request=request, config=config)
    return {'action': 'stop', 'target': asset_id}
