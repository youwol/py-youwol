from dataclasses import dataclass
from typing import Union

from starlette.websockets import WebSocket

from youwol_utils.context import WsContextLogger


@dataclass(frozen=False)
class WebSocketsStore:

    userChannel: Union[WebSocket, None] = None
    adminChannel: Union[WebSocket, None] = None


def web_socket_cache():

    return WebSocketsStore


class AdminContextLogger(WsContextLogger):
    def __init__(self):
        super().__init__(lambda: [WebSocketsStore.adminChannel])


class UserContextLogger(WsContextLogger):
    def __init__(self):
        super().__init__(lambda: [WebSocketsStore.adminChannel, WebSocketsStore.userChannel])

