from typing import Union

from dataclasses import dataclass
from starlette.websockets import WebSocket


@dataclass(frozen=False)
class WebSocketsCache:

    userChannel: Union[WebSocket, None] = None


def web_socket_cache():

    return WebSocketsCache
