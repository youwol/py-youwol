from dataclasses import dataclass
from typing import Union

from starlette.websockets import WebSocket, WebSocketDisconnect

from youwol_utils import log_info
from youwol_utils.context import WsContextReporter


@dataclass(frozen=False)
class WebSocketsStore:
    logs: Union[WebSocket, None] = None
    data: Union[WebSocket, None] = None


def web_socket_cache():
    return WebSocketsStore


class LogsStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: [WebSocketsStore.logs], mute_exceptions=True)


class WsDataStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: [WebSocketsStore.data], mute_exceptions=False)


async def start_web_socket(ws: WebSocket):
    await ws.accept()
    await ws.send_json({})
    while True:
        try:
            _ = await ws.receive_text()
        except WebSocketDisconnect:
            log_info(f'{ws.scope["client"]} - "WebSocket {ws.scope["path"]}" [disconnected]')
            break
