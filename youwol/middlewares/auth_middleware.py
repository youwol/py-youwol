from typing import Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.environment.youwol_environment import yw_config
from youwol.routers.authorization import get_user_info
from youwol.web_socket import WebSocketsStore
from youwol_utils.context import ContextFactory


class AuthMiddleware(BaseHTTPMiddleware):

    cache = {}

    def __init__(self, app: ASGIApp,
                 dispatch: DispatchFunction = None,
                 **_) -> None:
        super().__init__(app, dispatch)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        config = await yw_config()

        async with request.state.context.start(action=f"Authorisation middleware") as ctx:
            if not request.headers.get('authorization'):

                ctx.info(text="No authorisation token found")
                auth_token = await config.get_auth_token(context=ctx)
                # A bit ugly, not very safe ... coming from:
                # How to set request headers before path operation is executed
                # https://github.com/tiangolo/fastapi/issues/2727
                auth_header: Tuple[bytes, bytes] = "authorization".encode(), f"Bearer {auth_token}".encode()
                request.headers.__dict__["_list"].append(auth_header)

            if await self.authenticate(config.userEmail, request):
                ctx.info(text="User info retrieved", data=request.state.user_info)
                request.state.context = ctx
                response = await call_next(request)
            else:
                ctx.error(text="Unauthorized")
                response = Response(content="Unauthorized", status_code=403)
            return response

    async def authenticate(self, user_name: str, request: Request) -> bool:

        user_info = self.cache.get(user_name, None)
        if user_info:
            request.state.user_info = user_info
            return True

        user_info = await get_user_info(config=await yw_config())
        request.state.user_info = user_info
        self.cache[user_name] = user_info
        return True
