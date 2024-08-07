# standard library
from dataclasses import dataclass, field
from enum import Enum

# third parties
from starlette.websockets import WebSocket, WebSocketDisconnect

# Youwol utilities
from youwol.utils import log_info
from youwol.utils.context import WsContextReporter


@dataclass(frozen=False)
class WebSocketsStore:
    """
    Keep in memory the list of connected web-sockets from the `/ws-logs` and `/ws-data` channels.
    They are updated each time a channel is initialized or terminated through those end-points.

    See :func:`start_web_socket <youwol.app.web_socket.start_web_socket>`.
    """

    logs: list[WebSocket] = field(default_factory=list)
    """
    Channels regarding log message that do not convey logical meaning
    (e.g. :meth:`Context.info <youwol.utils.context.context.Context.info>`).
    """

    data: list[WebSocket] = field(default_factory=list)
    """
    Channels regarding log message that do convey logical meaning,
    generated from :meth:`Context.send <youwol.utils.context.context.Context.send>` method.
    """


global_ws_store = WebSocketsStore()


class LogsStreamer(WsContextReporter):
    """
    Implements :class:`WsContextReporter <youwol.utils.context.reporter.WsContextReporter>`
    to handle logs generated by the various :meth:`Context.info <youwol.utils.context.context.Context.info>`
     like methods.

    The purposes of these logs is to **not** convey logic information, they are send via the `/ws-logs` web socket
    of the application  (see :func:`create_app <youwol.app.fastapi_app.create_app>`).
    Because of this, exceptions are muted when sending messages.


    The `websockets_getter` of :class:`WsContextReporter <youwol.utils.context.reporter.WsContextReporter>`
    is provided from :attr:`WebSocketsStore.logs <youwol.app.web_socket.WebSocketsStore.logs>`.
    """

    def __init__(self):
        super().__init__(lambda: global_ws_store.logs, mute_exceptions=True)


class WsDataStreamer(WsContextReporter):
    """
    Implements :class:`WsContextReporter <youwol.utils.context.reporter.WsContextReporter>`
    to handle logs generated by the :meth:`Context.send <youwol.utils.context.context.Context.send>` method.

    The purposes of these logs is to convey logic information via the `/ws-data` web socket of the application
    (see :func:`create_app <youwol.app.fastapi_app.create_app>`).
    Because of this, exceptions are **not** muted when sending messages.

    The `websockets_getter` of :class:`WsContextReporter <youwol.utils.context.reporter.WsContextReporter>`
    is provided from :attr:`WebSocketsStore.data <youwol.app.web_socket.WebSocketsStore.data>`.
    """

    def __init__(self):
        super().__init__(lambda: global_ws_store.data, mute_exceptions=False)


class WsType(Enum):
    """
    Web socket channel type.
    """

    LOG = "Log"
    """
    Channel related to message that do not convey logical meaning for an application.
    """
    DATA = "Data"
    """
    Channel related to message that do convey logical meaning for an application.
    """


async def start_web_socket(ws: WebSocket, ws_type: WsType):
    """
    Function called when a new connection reach either `/ws-logs` and `/ws-data` end-points of the
    :glob:`application <youwol.app.fastapi_app.fastapi_app>`.

    The :class:`web socket store <youwol.app.web_socket.WebSocketsStore>` is updated appropriately when
    accepting the connection as well as at disconnection.

    Parameters:
        ws: the new websocket channel to connect
        ws_type: The type:
            * `Data` if coming from `/ws-data`
            * `Log` if coming from `/ws-logs`
    """
    channels = global_ws_store.data if ws_type == WsType.DATA else global_ws_store.logs
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
