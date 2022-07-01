from typing import List, Tuple, Optional, Union, Any

from fastapi import HTTPException
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.context import Context, Label


class Middleware(BaseHTTPMiddleware):

    def __init__(self,
                 app: ASGIApp,
                 auth_client,
                 cache_client,
                 unprotected_paths=lambda url: False,
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


class JwtProvider:

    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        raise NotImplementedError()


class JwtProviderBearer(JwtProvider):

    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        header_value = request.headers.get('Authorization')

        if not header_value:
            await context.info("No header Authorization")
            return None

        if header_value[:7] != "Bearer ":
            await context.info("Found header Authorization but no bearer")
            return None

        await context.info("Found bearer in header Authorization")
        return header_value[7:]


class JwtProviderCookie(JwtProvider):

    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        token = request.cookies.get('yw_jwt')

        if not token:
            await context.info("No cookie yw_jwt")
            return None

        await context.info("Found cookie yw_jwt")
        return token


class AuthMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp,
                 openid_base_url: Union[str, Any],
                 jwt_providers: List[JwtProvider] = None,
                 predicate_public_path=lambda url: False,
                 on_missing_token=lambda url: Response(content="Unauthorized", status_code=403),
                 dispatch: DispatchFunction = None):
        super().__init__(app, dispatch)
        self.predicate_public_path = predicate_public_path
        self.jwt_providers: List[JwtProvider] = [JwtProviderBearer()] + (jwt_providers if jwt_providers else [])
        self.on_missing_token = on_missing_token
        self.oidc_config = OidcConfig(openid_base_url) if isinstance(openid_base_url, str) else None
        self.openid_base_url = openid_base_url

    async def dispatch(self,
                       request: Request,
                       call_next: RequestResponseEndpoint
                       ) -> Response:

        async with Context.from_request(request).start(
                action="Authorization middleware",
                with_labels=[Label.MIDDLEWARE]
        ) as ctx:

            if self.predicate_public_path(request.url):
                await ctx.info(text="public path", data=request.url)
                return await call_next(request)

            token = None
            iter_jwt_providers = iter(self.jwt_providers)
            while token is None:
                try:
                    token = await next(iter_jwt_providers).get_token(request, ctx)
                except StopIteration:
                    break

            if token is None:
                await ctx.info("No JWT providers found a token")
                return self.on_missing_token(request.url)

            try:
                token_data = await (await self.get_oidc_config()).token_decode(token)
                await ctx.info(text="Token successfully decoded", data=token_data)
            except InvalidTokenError as error:
                await ctx.info(text="Invalid token", data=error)
                return Response(content=f"Invalid token : {error}", status_code=403)

            if not request.headers.get('Authorization'):
                await ctx.info("Setting bearer in Authorization header to found token")
                # A bit ugly, not very safe ... coming from:
                # How to set request headers before path operation is executed
                # https://github.com/tiangolo/fastapi/issues/2727
                auth_header: Tuple[bytes, bytes] = "authorization".encode(), f"Bearer {token}".encode()
                request.headers.__dict__["_list"].append(auth_header)

            request.state.user_info = token_data
            return await call_next(request)

    async def get_oidc_config(self):
        if isinstance(self.openid_base_url, str):
            return self.oidc_config

        current_oidc_base_url = await self.openid_base_url()
        if self.oidc_config is None or self.oidc_config.base_url != current_oidc_base_url:
            self.oidc_config = OidcConfig(current_oidc_base_url)
        return self.oidc_config
