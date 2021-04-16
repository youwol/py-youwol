from typing import Union

from dataclasses import dataclass
from starlette.websockets import WebSocket


@dataclass(frozen=False)
class WebSocketsCache:

    backends: WebSocket
    modules: WebSocket
    frontends: WebSocket
    assets: WebSocket
    environment: Union[WebSocket, None] = None
    api_gateway: Union[WebSocket, None] = None
    ui_gateway: Union[WebSocket, None] = None


def web_socket_cache():

    return WebSocketsCache
