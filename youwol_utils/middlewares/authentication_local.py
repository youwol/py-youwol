import aiohttp
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class AuthLocalMiddleware(BaseHTTPMiddleware):

    cache = {}
    url_base_auth = "http://localhost:2000/api/authorization"

    def __init__(self, app: ASGIApp,
                 dispatch: DispatchFunction = None,
                 **_) -> None:
        super().__init__(app, dispatch)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        user_name = request.headers.get('Authorization')
        if await self.authenticate(user_name, request):
            response = await call_next(request)
        else:
            response = Response(content="Unauthorized", status_code=403)
        return response

    async def authenticate(self, auth_token: str, request: Request) -> bool:

        user_info = self.cache.get(auth_token, None)
        if user_info:
            request.state.user_info = user_info
            return True
        excluded = ['content-length']
        headers = {k: v for k, v in request.headers.items() if k not in excluded}

        async with aiohttp.ClientSession() as session:
            async with await session.get(url=f"{self.url_base_auth}/user-info", headers=headers) as resp:
                if resp.status == 200:
                    user_info = await resp.json()
                    request.state.user_info = user_info
                    self.cache[auth_token] = user_info
                    return True
                return False
