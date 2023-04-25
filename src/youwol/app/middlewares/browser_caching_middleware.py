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
    Enabling the caching of assets by the browser can defeat the auto-fetching of resources
    to cache them in the user's computer.
    At the end, we only use the mechanism of py-youwol to handle caching of resources.
    """

    cache = {}

    def __init__(self, app: ASGIApp, dispatch: DispatchFunction = None, **_) -> None:
        super().__init__(app, dispatch)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if "/api/assets-gateway/raw/" in request.url.path and request.method == "GET":
            response.headers["Cache-Control"] = "no-cache, no-store"

        return response
