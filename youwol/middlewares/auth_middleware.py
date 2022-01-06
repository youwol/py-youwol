from typing import Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.context import Context
from youwol.web_socket import WebSocketsCache
from youwol.configuration.youwol_configuration import yw_config
from youwol.routers.authorization import get_user_info


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
        context = Context(
            web_socket=WebSocketsCache.api_gateway,
            config=config,
            request=request
            )

        if not request.headers.get('authorization'):
            auth_token = await config.get_auth_token(context=context)
            # A bit ugly, not very safe ... coming from:
            # How to set request headers before path operation is executed
            # https://github.com/tiangolo/fastapi/issues/2727
            auth_header: Tuple[bytes, bytes] = "authorization".encode(), f"Bearer {auth_token}".encode()
            request.headers.__dict__["_list"].append(auth_header)

        if await self.authenticate(config.userEmail, request):
            response = await call_next(request)
        else:
            response = Response(content="Unauthorized", status_code=403)
        return response

    async def authenticate(self, user_name: str, request: Request) -> bool:

        user_info = self.cache.get(user_name, None)
        if user_info:
            request.state.user_info = user_info
            return True

        user_info = await get_user_info(request=request, config=await yw_config())
        request.state.user_info = user_info
        self.cache[user_name] = user_info
        return True
