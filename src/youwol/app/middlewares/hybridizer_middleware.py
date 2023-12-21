# third parties
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Youwol utilities
from youwol.utils import YouWolException, youwol_exception_handler
from youwol.utils.context import Context, Label

# relative
from .local_cloud_hybridizers.abstract_local_cloud_dispatch import (
    AbstractLocalCloudDispatch,
)


class LocalCloudHybridizerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for hybrid local/cloud dispatching based on a set of dispatch rules that performs
    actions requiring a connection to the remote environment.

    A typical example is the
     [GetLoadingGraph](@yw-nav-class:youwol.app.middlewares.local_cloud_hybridizers.loading_graph_rules.GetLoadingGraph)
     dispatch: it allows to resolve dependencies by considering both:
    *  the modules available in the computer
    *  the modules available online.

    Note:
        Over the list of dispatches, only one at most is applied (the first one matching the incoming request).
    """

    dynamic_dispatch_rules: list[AbstractLocalCloudDispatch]
    """
    The list of dispatch evaluated by the middleware.
    """

    disabling_header: str
    """
    A header's key that, if present in the request's headers with a `'true'` value,
    disable the all middleware.
    """

    def __init__(
        self,
        app: ASGIApp,
        dynamic_dispatch_rules: list[AbstractLocalCloudDispatch],
        disabling_header: str,
    ) -> None:
        """
        Initializes a new instance.

        Parameters:
            app: ASGI application, forwarded to `BaseHTTPMiddleware`
            dynamic_dispatch_rules:
                set <a href="@yw-nav-attr:youwol.app.middlewares.hybridizer_middleware.LocalCloudHybridizerMiddleware
                .dynamic_dispatch_rules">dynamic_dispatch_rules</a>.
            disabling_header:
                set <a href="@yw-nav-attr:youwol.app.middlewares.hybridizer_middleware.LocalCloudHybridizerMiddleware
                .disabling_header">disabling_header</a>.
        """
        super().__init__(app)
        self.dynamic_dispatch_rules = dynamic_dispatch_rules
        self.disabling_header = disabling_header

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Call, in the order of the list, the `apply` method of the
        <a href="@yw-nav-attr:youwol.app.middlewares.hybridizer_middleware.LocalCloudHybridizerMiddleware.
        dynamic_dispatch_rules">dynamic_dispatch_rules</a>
        list until a first element return a response (not `None`).
        This response is returned as it is.

        If none of the dispatches match (all response received are `None`), the request proceed to its 'normal'
         destination.

        Parameters:
            request: The incoming request
            call_next: The next endpoint in the chain
        Return:
            The response after middleware processing.
        """
        async with Context.from_request(request).start(
            action="attempt hybrid local/cloud dispatches",
            with_labels=[Label.MIDDLEWARE],
        ) as ctx:
            if request.headers.get(self.disabling_header, "false") == "true":
                await ctx.warning(text="Dynamic dispatch disabled")
                return await call_next(request)

            for dispatch in self.dynamic_dispatch_rules:
                try:
                    match = await dispatch.apply(request, call_next, ctx)
                    if match:
                        return match
                except YouWolException as e:
                    return await youwol_exception_handler(request, e)

            await ctx.info(text="No dynamic dispatch match")

            await ctx.info(
                text="Request proceed to normal destination",
                data={"url": request.url.path},
            )

            return await call_next(request)
