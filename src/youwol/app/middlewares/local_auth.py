# standard library
import base64

# typing
from typing import Optional

# third parties
from starlette.requests import Request

# Youwol application
from youwol.app.environment import Authentication, AuthorizationProvider, DirectAuth
from youwol.app.environment.youwol_environment import YouwolEnvironment

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.clients.oidc.tokens_manager import Tokens, TokensManager
from youwol.utils.context import Context, ContextFactory
from youwol.utils.middlewares import JwtProvider


class NeedInteractiveSession(RuntimeError):
    def __init__(self):
        super().__init__("User need to be authenticated via authorization flow")


class JwtProviderPyYouwol(JwtProvider):
    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        try:
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
    )


async def get_local_tokens(
    auth_provider: AuthorizationProvider,
    auth_infos: Authentication,
) -> Tokens:
    tokens_id = local_tokens_id(auth_provider=auth_provider, auth_infos=auth_infos)

    oidc_client = OidcConfig(auth_provider.openidBaseUrl).for_client(
        auth_provider.openidClient
    )

    tokens_manager = TokensManager(
        cache=ContextFactory.with_static_data["auth_cache"], oidc_client=oidc_client
    )

    result = tokens_manager.restore_tokens(
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
