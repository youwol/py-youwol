# standard library
from dataclasses import dataclass, field
from enum import Enum

# typing
from typing import List

# third parties
from starlette.websockets import WebSocket, WebSocketDisconnect

# Youwol utilities
from youwol.utils import log_info
from youwol.utils.context import WsContextReporter


@dataclass(frozen=False)
class WebSocketsStore:
    logs: List[WebSocket] = field(default_factory=list)
    data: List[WebSocket] = field(default_factory=list)


global_ws_store = WebSocketsStore()


class LogsStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: global_ws_store.logs, mute_exceptions=True)


class WsDataStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: global_ws_store.data, mute_exceptions=False)


class WsType(Enum):
    Log = "Log"
    Data = "Data"


async def start_web_socket(ws: WebSocket, ws_type: WsType):
    channels = global_ws_store.data if ws_type == WsType.Data else global_ws_store.logs
    channels.append(ws)

    await ws.accept()
    await ws.send_json({})
    while True:
        try:
            _ = await ws.receive_text()
        except WebSocketDisconnect:
            log_info(
                f'{ws.scope["client"]} - "WebSocket {ws.scope["path"]}" [disconnected]'
            )
            channels.remove(ws)
            break
