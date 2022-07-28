from dataclasses import dataclass
from typing import Union

from starlette.websockets import WebSocket

from youwol_utils.context import WsContextReporter


@dataclass(frozen=False)
class WebSocketsStore:
    logs: Union[WebSocket, None] = None
    data: Union[WebSocket, None] = None


def web_socket_cache():
    return WebSocketsStore


class LogsStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: [WebSocketsStore.logs])


class WsDataStreamer(WsContextReporter):
    def __init__(self):
        super().__init__(lambda: [WebSocketsStore.data])
