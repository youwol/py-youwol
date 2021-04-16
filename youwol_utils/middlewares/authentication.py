from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class Middleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, auth_client, cache_client,
                 unprotected_paths,
                 dispatch: DispatchFunction = None,
                 **_) -> None:
        self.auth_client = auth_client
        self.cache_client = cache_client
        self.unprotected_paths = unprotected_paths
        super().__init__(app, dispatch)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        if self.unprotected_paths(request.url):
            response = await call_next(request)
        else:
            bearer_token = request.headers.get('Authorization')
            if await self.authenticate(bearer_token, request):
                response = await call_next(request)
            else:
                response = Response(content="Unauthorized", status_code=403)

        return response

    async def authenticate(self, bearer_token: str, request: Request) -> bool:
        if bearer_token is None:
            return False

        # Remove the Bearer prefix
        bearer_token = bearer_token[7:]

        user_info = await self.cache_client.get(name=bearer_token)
        ret = user_info is not None
        if not user_info:
            try:
                user_info = await self.auth_client.get_userinfo(bearer_token=bearer_token)
                ret = await self.cache_client.set(name=bearer_token, value=user_info, ex=3600)
            except HTTPException:
                return False

        request.state.user_info = user_info

        return ret
