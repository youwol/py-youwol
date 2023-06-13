# standard library
from urllib import parse

# typing
from typing import List, Optional

# third parties
from jwt import InvalidTokenError
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp

# Youwol utilities
from youwol.utils import CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcConfig, OidcInfos
from youwol.utils.clients.oidc.tokens_manager import TokensManager
from youwol.utils.context import Context, Label


class JwtProvider:
    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        raise NotImplementedError()


class JwtProviderBearer(JwtProvider):
    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        header_value = request.headers.get("Authorization")

        if not header_value:
            await context.info("No header Authorization")
            return None

        if header_value[:7] != "Bearer ":
            await context.info("Found header Authorization but no bearer")
            return None

        await context.info("Found bearer in header Authorization")
        return header_value[7:]


class JwtProviderCookie(JwtProvider):
    def __init__(self, auth_cache: CacheClient, openid_infos: OidcInfos):
        self.__cache = auth_cache
        self.openid_infos = openid_infos

    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        tokens_id = request.cookies.get("yw_jwt")

        if not tokens_id:
            await context.info("No cookie yw_jwt")
            return None

        client = OidcConfig(self.openid_infos.base_uri).for_client(
            self.openid_infos.client
        )
        tokens = TokensManager(
            cache=self.__cache,
            oidc_client=client,
        ).restore_tokens(
            tokens_id=tokens_id,
        )

        if tokens is None:
            await context.info("No tokens for existing cookie yw_jwt")
            return None

        await context.info("Found tokens for cookie yw_jwt")
        return await tokens.access_token()


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        openid_base_uri: str,
        jwt_providers: Optional[List[JwtProvider]] = None,
        predicate_public_path=lambda url: False,
        on_missing_token=lambda url: Response(content="Unauthorized", status_code=403),
        dispatch: Optional[DispatchFunction] = None,
    ):
        super().__init__(app, dispatch)
        self.predicate_public_path = predicate_public_path
        self.jwt_providers: List[JwtProvider] = [JwtProviderBearer()] + (
            jwt_providers if jwt_providers else []
        )
        self.on_missing_token = on_missing_token
        self.oidc_config = OidcConfig(openid_base_uri)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        async with Context.from_request(request).start(
            action="Authorization middleware", with_labels=[Label.MIDDLEWARE]
        ) as ctx:  # type: Context
            if self.predicate_public_path(request.url):
                await ctx.info(text="public path", data=str(request.url))
                return await call_next(request)

            access_token = None
            iter_jwt_providers = iter(self.jwt_providers)
            while access_token is None:
                try:
                    access_token = await next(iter_jwt_providers).get_token(
                        request, ctx
                    )
                except StopIteration:
                    break

            if access_token is None:
                await ctx.info("No JWT providers found a token")
                return self.on_missing_token(request.url)

            try:
                access_token_data = await self.oidc_config.token_decode(access_token)
                await ctx.info(text="Token successfully decoded")
                request.state.user_info = access_token_data
            except InvalidTokenError as error:
                await ctx.info(text="Invalid token", data={"error": error})
                return Response(content=f"Invalid token : {error}", status_code=403)

            if not request.headers.get("Authorization"):
                await ctx.info("Setting bearer in Authorization header to found token")
                ctx.with_headers["authorization"] = f"Bearer {access_token}"

            return await call_next(request)


def redirect_to_login(url):
    target_uri = parse.quote(str(url))
    login_flow = "auto"
    if str(url.query).find("login_flow=user") >= 0:
        login_flow = "user"
    if str(url.query).find("login_flow=temp") >= 0:
        login_flow = "temp"
    return RedirectResponse(
        f"/api/accounts/openid_rp/login?target_uri={target_uri}&flow={login_flow}",
        status_code=307,
    )
