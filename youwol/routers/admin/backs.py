import asyncio

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.websockets import WebSocket

from dashboard.back.src.routers.admin.web_socket_cache import WebSocketsCache
from env.utils import get_cached_environment
from global_configuration import GlobalConfiguration

from service.models import ServiceStatus, BackEnd
from service.utils import get_health_status

router = APIRouter()


class ActionService(BaseModel):
    action: str
    target: str


def get_current_environment():
    global_config = GlobalConfiguration()
    return get_cached_environment(global_config)


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.backs = ws
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Message text was: {data}")


@router.get("/status",
            summary="status")
async def status():

    env = get_current_environment()
    selected = [s for s in env.services.get() if isinstance(s, BackEnd)]
    health_status = await get_health_status(gateway_url=env.gateway_url, services=selected)
    services_status = {s: {'health': health_status[s], 'deployed': ServiceStatus(code=200)} for s in selected}
    return [{"name": k.name, "health": s["health"][0], "deployed": s["deployed"]} for k, s in services_status.items()]


@router.post("/start", summary="start non running backend")
async def start():

    healths = await status()
    to_starts = [s['name'] for s in healths if s['health'] != 200]
    await asyncio.gather(*[start(name) for name in to_starts])
    return {}


@router.post("/restart", summary="start non running backend")
async def restart():

    healths = await status()
    to_stops = [s['name'] for s in healths if s['health'] == 200]

    await asyncio.gather(*[stop(name) for name in to_stops])

    to_starts = to_stops
    await asyncio.gather(*[start(name) for name in to_starts])

    return {}


@router.post("/{name}/start", summary="execute action")
async def start(name: str):

    ws = WebSocketsCache.backs
    env = get_current_environment()
    ws and await ws.send_json({"action": "serve", "step": "started", "target": name})
    asyncio.run_coroutine_threadsafe(env.start(name, ws), asyncio.get_event_loop())
    s = next(s for s in env.services.get() if s.name == name)
    for i in range(10):
        await asyncio.sleep(0.5)
        health = await s.health(gateway_url=env.gateway_url)
        if health == ServiceStatus(code=200):
            ws and await ws.send_json({"action": "serve", "step": "serving", "target": name})
            return

    return {'action': 'start', 'target': name}


@router.post("/{name}/stop", summary="execute action")
async def stop(name: str):

    ws = WebSocketsCache.backs
    env = get_current_environment()
    env.kill(name)
    ws and await ws.send_json({"action": "serve", "step": "done", "target": name})
    return {'action': 'stop', 'target': name}
