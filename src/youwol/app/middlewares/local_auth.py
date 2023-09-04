# standard library
import base64

from abc import ABC, abstractmethod

# typing
from typing import Optional, Tuple

# third parties
from starlette.requests import Request

# Youwol application
from youwol.app.environment import (
    Authentication,
    AuthorizationProvider,
    BrowserAuth,
    DirectAuth,
)
from youwol.app.environment.youwol_environment import YouwolEnvironment

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.clients.oidc.tokens_manager import (
    Tokens,
    TokensManager,
    TokensStorage,
)
from youwol.utils.context import Context
from youwol.utils.middlewares import JwtProvider, JwtProviderBearer, JwtProviderCookie


class NeedInteractiveSession(RuntimeError):
    def __init__(self):
        super().__init__("User need to be authenticated via authorization flow")


class JwtProviderDynamicIssuer(JwtProvider, ABC):
    @abstractmethod
    async def _get_token(self, request: Request, context: Context) -> Optional[str]:
        raise NotImplementedError()

    async def get_token_and_openid_base_url(
        self, request: Request, context: Context
    ) -> Tuple[Optional[str], str]:
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        token = await self._get_token(request=request, context=context)
        if token is None:
            return None, ""
        openid_base_url = env.get_remote_info().authProvider.openidBaseUrl
        return token, openid_base_url


class JwtProviderDelegatingDynamicIssuer(JwtProviderDynamicIssuer, ABC):
    async def _get_token(self, request: Request, context: Context) -> Optional[str]:
        return (
            await self._get_delegate().get_token_and_openid_base_url(
                request=request, context=context
            )
        )[0]

    @abstractmethod
    def _get_delegate(self) -> JwtProvider:
        raise NotImplementedError()


class JwtProviderBearerDynamicIssuer(JwtProviderDelegatingDynamicIssuer):
    def _get_delegate(self) -> JwtProvider:
        return JwtProviderBearer(openid_base_url="")


class JwtProviderCookieDynamicIssuer(JwtProviderDelegatingDynamicIssuer):
    def __init__(self, tokens_manager: TokensManager):
        self.__delegate = JwtProviderCookie(
            tokens_manager=tokens_manager, openid_base_url=""
        )

    def _get_delegate(self) -> JwtProvider:
        return self.__delegate


class JwtProviderPyYouwol(JwtProviderDynamicIssuer):
    async def _get_token(self, request: Request, context: Context) -> Optional[str]:
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        try:
            if isinstance(env.get_authentication_info(), BrowserAuth):
                return None

            tokens = await get_connected_local_tokens(context=context)
            access_token = await tokens.access_token()
            return access_token
        except NeedInteractiveSession:
            return None


def local_tokens_id(
    auth_provider: AuthorizationProvider, auth_infos: Authentication
) -> str:
    key_string = f"{auth_provider.openidBaseUrl}_{auth_provider.openidClient.client_id}_{auth_infos.authId}"
    return (
        f"local_{base64.b64encode(key_string.encode(encoding='UTF8')).decode('UTF8')}"
    )


async def get_connected_local_tokens(context: Context) -> Tokens:
    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)

    return await get_local_tokens(
        auth_provider=env.get_remote_info().authProvider,
        auth_infos=env.get_authentication_info(),
        tokens_storage=env.tokens_storage,
    )


async def get_local_tokens(
    tokens_storage: TokensStorage,
    auth_provider: AuthorizationProvider,
    auth_infos: Authentication,
) -> Tokens:
    tokens_id = local_tokens_id(auth_provider=auth_provider, auth_infos=auth_infos)

    oidc_client = OidcConfig(auth_provider.openidBaseUrl).for_client(
        auth_provider.openidClient
    )

    tokens_manager = TokensManager(
        storage=tokens_storage,
        oidc_client=oidc_client,
    )

    result = await tokens_manager.restore_tokens(
        tokens_id=tokens_id,
    )

    if result is None:
        if isinstance(auth_infos, DirectAuth):
            tokens_data = await oidc_client.direct_flow(
                username=auth_infos.userName, password=auth_infos.password
            )
            result = await tokens_manager.save_tokens(
                tokens_id=tokens_id,
                tokens_data=tokens_data,
            )
        else:
            raise NeedInteractiveSession()

    return result
