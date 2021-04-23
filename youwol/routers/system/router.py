from fastapi import APIRouter, WebSocket
from youwol.web_socket import WebSocketsCache


router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.system = ws
    await ws.send_json({})
    while True:
        _ = await ws.receive_text()


