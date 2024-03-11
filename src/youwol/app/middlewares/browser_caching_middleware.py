# standard library
import json
import urllib.parse

# typing
from typing import Literal

# third parties
from pydantic import BaseModel
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Youwol application
from youwol.app.environment.youwol_environment import (
    YouwolEnvironment,
    YouwolEnvironmentFactory,
)

# Youwol utilities
from youwol.utils import Context
from youwol.utils.crypto.digest import compute_digest


class LocalYouwolCookie(BaseModel):
    """
    Model representation of the local YouWol environment cookie.
    """

    type: Literal["local"] = "local"
    """
    A literal indicator of the environment type, which is always 'local' for instances of this class.
    """

    port: int
    """
    The port number on which the local YouWol server is running.
    """

    wsDataUrl: str
    """
    The WebSocket URL used for data communications with the local YouWol server.
    """

    wsLogUrl: str
    """
    The WebSocket URL used for log communications with the local YouWol server.
    """


class BrowserMiddleware(BaseHTTPMiddleware):
    """
    Middleware to control interaction with browser regarding caching, cookies, *etc.*.
    """

    cache = {}

    def __init__(
        self,
        app: ASGIApp,
        dispatch: DispatchFunction | None = None,
        config_dependant_browser_caching=False,
        **_,
    ) -> None:
        """
        Initializes a new instance of BrowserMiddleware.

        Parameters:
           app: The ASGI application, forwarded to `BaseHTTPMiddleware`.
           config_dependant_browser_caching: Enable cache dependent_browser_cache
           dispatch: The dispatch function, forwarded to `BaseHTTPMiddleware`.
        """
        super().__init__(app, dispatch)
        self.config_dependant_browser_caching = config_dependant_browser_caching

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Middleware logic to control interaction with browser:
            *  set up the [`youwol` cookie](@yw-nav-class:LocalYouwolCookie).

        Parameters:
            request: The incoming request.
            call_next: The next endpoint in the chain.

        Returns:
            The response with eventually modified headers.
        """
        response = await call_next(request)
        if self.config_dependant_browser_caching:
            digest = compute_digest(
                {
                    "config_digest": YouwolEnvironmentFactory.get_digest(),
                    "user_info": (
                        {
                            "name": request.state.user_info["sub"],
                            "groups": request.state.user_info["memberof"],
                        }
                        if hasattr(request.state, "user_info")
                        else None
                    ),
                },
                trace_path_root="browser_caching_middleware",
            ).hex()
            response.headers["Youwol-Config-Digest"] = digest
            response.set_cookie("youwol-config-digest", digest)
            response.headers["Vary"] = "Youwol-Config-Digest, Cookie"
            response.headers["Cache-Control"] = "max-age=3600"

        context: Context = request.state.context
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        yw_cookie = LocalYouwolCookie(
            port=env.httpPort, wsDataUrl="ws-data", wsLogUrl="ws-log"
        )
        response.set_cookie(
            "youwol", urllib.parse.quote(json.dumps(yw_cookie.__dict__))
        )

        return response
