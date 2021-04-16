import asyncio
import itertools
from fastapi import APIRouter, WebSocket, Depends
from starlette.requests import Request

from youwol.configuration.user_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config, YouwolConfigurationFactory
from youwol.context import Context, Action
from youwol.routers.commons import SkeletonsResponse, list_skeletons, PostSkeletonBody, create_skeleton
from youwol.routers.frontends.models import StatusResponse, AllStatusResponse
from youwol.routers.frontends.utils import ping, get_all_fronts, FrontEnd, serve, kill
from youwol.routers.ui import redirect_get_ui
from youwol.web_socket import WebSocketsCache
from youwol.routers.environment.router import status as env_status

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.frontends = ws
    await ws.send_json({})
    while True:
        _ = await ws.receive_text()


@router.get("/status",
            response_model=AllStatusResponse,
            summary="status")
async def status(request: Request, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(request=request, config=config, web_socket=WebSocketsCache.frontends)
    all_fronts = await get_all_fronts(context)

    async def is_healthy(front: FrontEnd):
        ui_status = await redirect_get_ui(request, front.info.name, 'index.html', config)
        return ui_status.status_code == 200

    async def is_serving(front: FrontEnd):
        if not front.pipeline.serve:
            return None
        return await ping(f"http://localhost:{front.info.port}")

    dev_servers = await asyncio.gather(*[is_serving(front) for front in all_fronts])
    healths = await asyncio.gather(*[is_healthy(front) for front in all_fronts])
    all_status = [StatusResponse(name=front.info.name,
                                 health=health,
                                 url=f"/ui/{front.info.name}",
                                 devServer=dev_server)
                  for front, health, dev_server in zip(all_fronts, healths, dev_servers)]

    resp = AllStatusResponse(status=all_status)
    WebSocketsCache.frontends and await WebSocketsCache.frontends.send_json({
        **{"type": "Status"},
        **resp.dict()
        })

    return resp


@router.post("/{name}/start", summary="execute action")
async def start(request: Request, name: str, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(config=config, web_socket=WebSocketsCache.frontends).with_target(name)
    all_fronts = await get_all_fronts(context)
    target = next(f for f in all_fronts if f.info.name == name)

    async def start_serving(t: FrontEnd):
        async with context.with_target(name).start(Action.SERVE) as ctx:
            await serve(t, context=ctx)
            await status(request=request, config=config)

    asyncio.run_coroutine_threadsafe(start_serving(target), asyncio.get_event_loop())

    return {'action': 'start', 'target': name}


@router.post("/{name}/stop", summary="execute action")
async def stop(name: str, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(config=config, web_socket=WebSocketsCache.frontends).with_target(name)
    all_fronts = await get_all_fronts(context)
    target = next(f for f in all_fronts if f.info.name == name)
    await kill(target)

    return {'action': 'stop', 'target': name}


@router.get("/skeletons",
            response_model=SkeletonsResponse,
            summary="list the available skeletons")
async def skeletons(
        config: YouwolConfiguration = Depends(yw_config)
        ):

    resp = await list_skeletons(pipelines=config.userConfig.frontends.pipelines)
    return resp


@router.post("/skeletons/{pipeline}",
             summary="create skeleton")
async def post_skeletons(
        request: Request,
        pipeline: str,
        body: PostSkeletonBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(request=request, config=config, web_socket=WebSocketsCache.frontends)
    pipeline = config.userConfig.frontends.pipelines[pipeline]
    skeleton = await create_skeleton(body=body, pipeline=pipeline, context=context)
    await YouwolConfigurationFactory.reload()
    new_conf = await yw_config()
    await env_status(request, new_conf)
    return skeleton
