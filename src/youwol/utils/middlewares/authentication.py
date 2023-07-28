# standard library
from abc import ABC, abstractmethod
from urllib import parse

# typing
from typing import Dict, List, Optional, Tuple, Union

# third parties
from jwt import InvalidTokenError, PyJWKClientError
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.clients.oidc.tokens_manager import TokensManager
from youwol.utils.context import Context, Label


class JwtProvider(ABC):
    @abstractmethod
    async def get_token_and_openid_base_url(
        self, request: Request, context: Context
    ) -> Tuple[Optional[str], str]:
        raise NotImplementedError()


class JwtProviderBearer(JwtProvider):
    def __init__(self, openid_base_url: str):
        self.__openid_base_url = openid_base_url

    async def get_token_and_openid_base_url(
        self, request: Request, context: Context
    ) -> Tuple[Optional[str], str]:
        header_value = request.headers.get("Authorization")

        if not header_value:
            await context.info("No header Authorization")
            return None, ""

        if header_value[:7] != "Bearer ":
            await context.info("Found header Authorization but no bearer")
            return None, ""

        await context.info("Found bearer in header Authorization")
        return header_value[7:], self.__openid_base_url


class JwtProviderCookie(JwtProvider):
    def __init__(self, tokens_manager: TokensManager, openid_base_url: str):
        self.__tokens_manager = tokens_manager
        self.__openid_base_url = openid_base_url

    async def get_token_and_openid_base_url(
        self, request: Request, context: Context
    ) -> Tuple[Optional[str], str]:
        tokens_id = request.cookies.get("yw_jwt")

        if not tokens_id:
            await context.info("No cookie yw_jwt")
            return None, ""

        tokens = await self.__tokens_manager.restore_tokens(
            tokens_id=tokens_id,
        )

        if tokens is None:
            await context.info("No tokens for existing cookie yw_jwt")
            return None, ""

        await context.info("Found tokens for cookie yw_jwt")
        return await tokens.access_token(), self.__openid_base_url


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        jwt_providers: Union[JwtProvider, List[JwtProvider]],
        predicate_public_path=lambda url: False,
        on_missing_token=lambda url, text: Response(
            content=f"Authentication failure : {text}", status_code=403
        ),
        dispatch: Optional[DispatchFunction] = None,
    ):
        super().__init__(app, dispatch)
        self.predicate_public_path = predicate_public_path
        if not isinstance(jwt_providers, List):
            jwt_providers = [jwt_providers]
        self.jwt_providers = jwt_providers
        self.on_missing_token = on_missing_token
        self.__oidc_config_cache: Dict[str, OidcConfig] = {}

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
            openid_base_url = None
            iter_jwt_providers = iter(self.jwt_providers)
            while access_token is None:
                try:
                    access_token, openid_base_url = await next(
                        iter_jwt_providers
                    ).get_token_and_openid_base_url(request, ctx)
                except StopIteration:
                    break

            if access_token is None:
                await ctx.info("No JWT providers found a token")
                return self.on_missing_token(request.url, "No access token")

            try:
                if openid_base_url not in self.__oidc_config_cache:
                    self.__oidc_config_cache[openid_base_url] = OidcConfig(
                        base_url=openid_base_url
                    )

                access_token_data = await self.__oidc_config_cache[
                    openid_base_url
                ].token_decode(access_token)
                await ctx.info(text="Token successfully decoded")
                request.state.user_info = access_token_data
            except PyJWKClientError as error:
                await ctx.info(text="Invalid issuer", data={"error": error})
                return self.on_missing_token(request.url, str(error))
            except InvalidTokenError as error:
                await ctx.info(text="Invalid token", data={"error": error})
                return self.on_missing_token(request.url, str(error))

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
