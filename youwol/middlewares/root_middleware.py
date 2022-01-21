from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.web_socket import WebSocketsStore
from youwol_utils.context import ContextFactory, Context


class RootMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp,
                 dispatch: DispatchFunction = None,
                 **_) -> None:
        super().__init__(app, dispatch)

    @staticmethod
    def get_context(request: Request, web_socket, **kwargs):
        try:
            context = request.state.context
            return context
        except AttributeError:
            return Context(request=request,
                           web_socket=web_socket,
                           with_data={**ContextFactory.with_static_data, **kwargs})

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:

        context = self.get_context(request=request, web_socket=WebSocketsStore.adminChannel)

        async with context.start(
                action=f"{request.url.path.split('/')[-1]}",
                with_attributes={
                    'method': request.method,
                    'targetService': request.url.path.split('/')[2:3]
                }
        ) as ctx:
            request.state.context = ctx
            ctx.info(
                text='request info',
                data={
                    'url': request.url.path,
                    'method': request.method,
                    'headers': {k: v for k, v in request.headers.items()}
                })
            return await call_next(request)
