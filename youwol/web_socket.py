from dataclasses import dataclass, field
from enum import Enum
from typing import List

from starlette.websockets import WebSocket, WebSocketDisconnect
from youwol_utils import log_info

from youwol_utils.context import WsContextReporter


@dataclass(frozen=False)
class WebSocketsStore:
    logs: List[WebSocket] = field(default_factory=list)
    data: List[WebSocket] = field(default_factory=list)


global_ws_store = None


def web_sockets_store():
    global global_ws_store
    if global_ws_store:
        return global_ws_store
    global_ws_store = WebSocketsStore()
    return global_ws_store


class LogsStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: web_sockets_store().logs, mute_exceptions=True)


class WsDataStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: web_sockets_store().data, mute_exceptions=False)


class WsType(Enum):
    Log = "Log"
    Data = "Data"


async def start_web_socket(
        ws: WebSocket,
        ws_type: WsType
        ):
    ws_store = web_sockets_store()
    channels = ws_store.data if ws_type == WsType.Data else ws_store.logs
    channels.append(ws)

    await ws.accept()
    await ws.send_json({})
    while True:
        try:
            _ = await ws.receive_text()
        except WebSocketDisconnect:
            log_info(f'{ws.scope["client"]} - "WebSocket {ws.scope["path"]}" [disconnected]')
            channels.remove(ws)
            break
