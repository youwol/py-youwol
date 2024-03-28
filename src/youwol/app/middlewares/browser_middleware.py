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
from youwol.app.environment.youwol_environment import YouwolEnvironment

# Youwol utilities
from youwol.utils import Context, Label


class WebPmCookie(BaseModel):
    """
    Defines the WebPM server configuration.
    It is consumed by the library `@youwol/webpm`.
    """

    pathLoadingGraph: str
    """
    Path to retrieve the loading graphs.
    """
    pathResource: str
    """
    Path to retrieve a resource.
    """
    pathPypi: str
    """
    Path to the emulated PyPi index.
    """
    pathPyodide: str
    """
    Path to the emulated Pyodide index.
    """


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

    origin: str
    """
    Origin of the server
    """

    webpm: WebPmCookie
    """
    WebPM server configuration.
    """


class BrowserMiddleware(BaseHTTPMiddleware):
    """
    Middleware to control interaction with browser regarding caching, headers, cookies, *etc.*.

    It is configured from the [BrowserCache](@yw-nav-class:models_config.BrowserCache) class.
    """

    def __init__(
        self,
        app: ASGIApp,
        dispatch: DispatchFunction | None = None,
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

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Middleware logic to control interaction with browser:
            *  Eventually retrieves/caches responses from the [BrowserCacheStore](@yw-nav-class:BrowserCacheStore).
            If a response is cached with `BrowserCacheStore`, `Cache-Control` header is set to `no-cache, no-store`.
            *  Set up the [`youwol` cookie](@yw-nav-class:LocalYouwolCookie).
            *  Apply `onEnter` and `onExit` user defined callbacks
             (see [BrowserCache](@yw-nav-class:models_config.BrowserCache)) at the start & end of the processing.

        Parameters:
            request: The incoming request.
            call_next: The next endpoint in the chain.

        Returns:
            The response with eventually modified headers.
        """

        def apply_final_transform(resp: Response, is_cached: bool):
            if browser_env.onExit:
                resp = browser_env.onExit(request, resp, ctx)
            if is_cached:
                resp.headers["Cache-Control"] = "no-cache, no-store"
            return resp

        async with Context.from_request(request).start(
            action="Browser middleware",
            with_labels=[Label.MIDDLEWARE],
        ) as ctx:
            env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
            browser_env = env.configuration.system.browserEnvironment
            cache = env.browserCacheStore
            cached_resp = await cache.try_get(request=request, context=ctx)
            if cached_resp:
                await ctx.info(
                    text="Resource retrieved from cache", data=cached_resp.item
                )
                return apply_final_transform(cached_resp.response, is_cached=True)

            if browser_env.onEnter:
                request = browser_env.onEnter(request, ctx)

            response = await call_next(request)

            yw_cookie = LocalYouwolCookie(
                port=env.httpPort,
                wsDataUrl="ws-data",
                wsLogUrl="ws-log",
                origin=f"http://localhost:{env.httpPort}",
                webpm=WebPmCookie(
                    pathLoadingGraph="/api/assets-gateway/cdn-backend/queries/loading-graph",
                    pathResource="/api/assets-gateway/cdn-backend/resources",
                    pathPypi="/python/pypi",
                    pathPyodide="/python/pyodide",
                ),
            )
            response.set_cookie(
                "youwol", urllib.parse.quote(json.dumps(yw_cookie.dict()))
            )

            persisted = await cache.cache_if_needed(
                request=request, response=response, context=ctx
            )
            if persisted:
                await ctx.info(text="Resource persisted in cache", data=persisted)

            return apply_final_transform(response, is_cached=persisted is not None)
