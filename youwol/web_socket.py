from dataclasses import dataclass
from typing import Union

from starlette.websockets import WebSocket


@dataclass(frozen=False)
class WebSocketsStore:

    userChannel: Union[WebSocket, None] = None


def web_socket_cache():

    return WebSocketsStore
