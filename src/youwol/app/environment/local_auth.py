# standard library
import base64

from abc import ABC, abstractmethod

# typing
from typing import Optional

# third parties
from starlette.requests import Request

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.clients.oidc.tokens_manager import (
    Tokens,
    TokensManager,
    TokensStorage,
)
from youwol.utils.context import Context
from youwol.utils.middlewares import JwtProvider, JwtProviderBearer, JwtProviderCookie

# relative
from .models import Authentication, AuthorizationProvider, BrowserAuth, DirectAuth
from .youwol_environment import YouwolEnvironment


class NeedInteractiveSession(RuntimeError):
    def __init__(self):
        super().__init__("User need to be authenticated via authorization flow")


class JwtProviderDynamicIssuer(JwtProvider, ABC):
    """
    Abstract dynamic JWT provider issuer w/ the target remote environment.

    """

    @abstractmethod
    async def _get_token(self, request: Request, context: Context) -> Optional[str]:
        """
        Define abstract method interface.

        Parameters:
            request: incoming request.
            context: current context

        Return:
             The JWT token.
        """
        raise NotImplementedError()

    async def get_token_and_openid_base_url(
        self, request: Request, context: Context
    ) -> tuple[Optional[str], str]:
        """
        Use the abstract `_get_token` method to implement
        <a href="@yw-nav-class:youwol.utils.middlewares.authentication.JwtProvider.get_token_and_openid_base_url">
        JwtProvider.get_token_and_openid_base_url</a>.

        Parameters:
            request: incoming request.
            context: current context, used to retrieve the connected remote environment.

        Return:
            A tuple of string with optional JWT token and openId base URL.
        """
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        token = await self._get_token(request=request, context=context)
        if token is None:
            return None, ""
        openid_base_url = env.get_remote_info().authProvider.openidBaseUrl
        return token, openid_base_url


class JwtProviderDelegatingDynamicIssuer(JwtProviderDynamicIssuer, ABC):
    """
    Abstract delegating dynamic JWT provider issuer.
    """

    async def _get_token(self, request: Request, context: Context) -> Optional[str]:
        """
        Use the abstract `_get_delegate` method to implement
        <a href="@yw-nav-class:youwol.app.environment.local_auth.JwtProviderDynamicIssuer._get_token">
        JwtProviderDynamicIssuer._get_token</a>.

        Parameters:
            request: incoming request.
            context: current context, used to retrieve the connected remote environment.

        Return:
            JWT token.
        """
        return (
            await self._get_delegate().get_token_and_openid_base_url(
                request=request, context=context
            )
        )[0]

    @abstractmethod
    def _get_delegate(self) -> JwtProvider:
        """
        Define abstract method interface.

        Return:
             The JWT provider delegate.
        """
        raise NotImplementedError()


class JwtProviderBearerDynamicIssuer(JwtProviderDelegatingDynamicIssuer):
    """
    Delegating dynamic JWT provider issuer using
    [JwtProviderBearer](@yw-nav-class:youwol.utils.middlewares.authentication.JwtProviderBearer).
    """

    def _get_delegate(self) -> JwtProvider:
        """
        Implement
        <a href="@yw-nav-meth:youwol.app.environment.local_auth.JwtProviderDelegatingDynamicIssuer._get_delegate">
        JwtProviderDelegatingDynamicIssuer._get_delegate</a>

        Return:
            The [JwtProviderBearer](@yw-nav-class:youwol.utils.middlewares.authentication.JwtProviderBearer) delegate.
        """
        return JwtProviderBearer(openid_base_url="")


class JwtProviderCookieDynamicIssuer(JwtProviderDelegatingDynamicIssuer):
    """
    Delegating dynamic JWT provider issuer using
    [JwtProviderCookie](@yw-nav-class:youwol.utils.middlewares.authentication.JwtProviderCookie).
    """

    __delegate: JwtProviderCookie
    """
    Instantiated delegate.
    """

    def __init__(self, tokens_manager: TokensManager):
        """
        Instantiate
        <a href="@yw-nav-meth:youwol.app.environment.local_auth.JwtProviderCookieDynamicIssuer.__delegate">
        JwtProviderCookieDynamicIssuer.__delegate</a>
        from the tokens manager.

        Parameters:
            tokens_manager: tokens manager

        """
        self.__delegate = JwtProviderCookie(
            tokens_manager=tokens_manager, openid_base_url=""
        )

    def _get_delegate(self) -> JwtProvider:
        """
        Implement
        <a href="@yw-nav-meth:youwol.app.environment.local_auth.JwtProviderDelegatingDynamicIssuer._get_delegate">
        JwtProviderDelegatingDynamicIssuer._get_delegate</a>

        Return:
            The [JwtProviderCookie](@yw-nav-class:youwol.utils.middlewares.authentication.JwtProviderCookie) delegate.
        """
        return self.__delegate


class JwtProviderPyYouwol(JwtProviderDynamicIssuer):
    """
    PyYouwol JWT provider.
    """

    async def _get_token(self, request: Request, context: Context) -> Optional[str]:
        """
        Implement
        <a href="@yw-nav-class:youwol.app.environment.local_auth.JwtProviderDynamicIssuer._get_token">
        JwtProviderDynamicIssuer._get_token</a>.

        Parameters:
            request: incoming request.
            context: current context, used to retrieve the connected remote environment.

        Return:
            JWT token.
        """
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
    """
    Use the active CloudEnvironment to retrieve the auth. token using
    [get_local_tokens](@yw-nav-func:youwol.app.environment.local_auth.get_local_tokens).

    Parameters:
        context: current context, used to retrieve the connected remote environment & tokens storage.

    Return:
        The tokens
    """
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
    """
    Retrieve local auth. token from explicit target.

    Parameters:
        tokens_storage: a token storage
        auth_provider: an auth. provider
        auth_infos: authentication info

    Return:
        Tokens
    """
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
