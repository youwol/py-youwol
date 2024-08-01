# third parties
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
from youwol.utils import Context, Label, decode_id
from youwol.utils.request_info_factory import url_match


class EsmServersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to dispatch requests targeting ESM components served by an ESM live server.
    """

    notServedResources: list[str] = [
        ".yw_metadata.json",
        "dist/docs",
        "coverage",
        "dist/bundle-analysis.html",
    ]

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
        Dispatch.

        Parameters:
            request: Incoming request.
            call_next: Next layer in the middleware chain.

        Returns:
            The response.
        """
        async with Context.from_request(request).start_middleware(
            action="EsmServersMiddleware",
            with_labels=[Label.MIDDLEWARE],
        ) as ctx:
            env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
            if not env.proxied_esm_servers.store:
                return await call_next(request)
            is_matching, params = url_match(
                request, "GET:/api/assets-gateway/cdn-backend/resources/*/*/**"
            )
            if not is_matching:
                return await call_next(request)

            package = decode_id(params[0])
            version = params[1]
            esm_proxy = env.proxied_esm_servers.get(package, version)
            if not esm_proxy:
                return await call_next(request)

            return await esm_proxy.apply(request=request, target=params[2], context=ctx)
