from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol.configuration.youwol_configuration import yw_config
from youwol.routers.api import get_user_info


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
