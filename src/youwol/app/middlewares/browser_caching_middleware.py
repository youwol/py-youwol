# typing

# third parties
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Youwol utilities
from youwol.utils.crypto.digest import compute_digest

# relative
from ..environment.youwol_environment import YouwolEnvironmentFactory


class BrowserCachingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to control browser caching.
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
        Initializes a new instance of BrowserCachingMiddleware.

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

        return response
