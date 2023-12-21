# typing
from typing import Optional

# third parties
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class BrowserCachingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to control browser caching.
    """

    cache = {}

    def __init__(
        self, app: ASGIApp, dispatch: Optional[DispatchFunction] = None, **_
    ) -> None:
        """
        Initializes a new instance of BrowserCachingMiddleware.

        Parameters:
           app: The ASGI application, forwarded to `BaseHTTPMiddleware`.
           dispatch: The dispatch function, forwarded to `BaseHTTPMiddleware`.
        """
        super().__init__(app, dispatch)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Middleware logic to control browser caching.
        For now, it disables browser cache by setting the header `Cache-Control` to `no-cache, no-store`
        for destination matching `/api/assets-gateway/raw/**`.

        Parameters:
            request: The incoming request.
            call_next: The next endpoint in the chain.

        Returns:
            The response with eventually modified headers.
        """
        response = await call_next(request)
        if "/api/assets-gateway/raw/" in request.url.path and request.method == "GET":
            response.headers["Cache-Control"] = "no-cache, no-store"

        return response
