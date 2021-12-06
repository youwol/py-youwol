from typing import Union

from dataclasses import dataclass
from starlette.websockets import WebSocket


@dataclass(frozen=False)
class WebSocketsCache:

    regularChannel: WebSocket

    backends: WebSocket
    modules: WebSocket
    frontends: WebSocket
    assets: WebSocket
    upload_packages: WebSocket
    download_packages: WebSocket
    upload_flux_apps: WebSocket
    upload_stories: WebSocket
    upload_data: WebSocket
    download_flux_apps: WebSocket
    local_cdn: WebSocket

    system: Union[WebSocket, None] = None

    environment: Union[WebSocket, None] = None
    api_gateway: Union[WebSocket, None] = None
    ui_gateway: Union[WebSocket, None] = None


def web_socket_cache():

    return WebSocketsCache
