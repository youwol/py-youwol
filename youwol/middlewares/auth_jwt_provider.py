from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel
from starlette.requests import Request
from youwol.environment import AuthorizationProvider, Authentication, DirectAuth, BrowserAuth

from youwol.environment.youwol_environment import YouwolEnvironment
from youwol_utils import CacheClient
from youwol_utils.clients.oidc.oidc_config import OidcInfos, OidcConfig
from youwol_utils.context import Context
from youwol_utils.middlewares import JwtProvider, JwtProviderCookie


class DeadlinedCache(BaseModel):
    value: Any
    deadline: float
    dependencies: Dict[str, str]

    def is_valid(self, dependencies) -> bool:

        for k, v in self.dependencies.items():
            if k not in dependencies or dependencies[k] != v:
                return False
        margin = self.deadline - datetime.timestamp(datetime.now())
        return margin > 0


class JwtProviderPyYouwol(JwtProvider):
    """
    This class hides some 'code smells':

    *  usage of two caching mechanisms, one should be able to cover both usages
    *  static nature of the caches
    *  'request = context.request' used in get_auth_token_cookie
    """
    __tokens_cache: List[DeadlinedCache] = []
    __jwt_cache: CacheClient

    def __init__(self, jwt_cache: CacheClient):
        JwtProviderPyYouwol.__jwt_cache = jwt_cache

    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        # get auth token of current connection
        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)

        return await JwtProviderPyYouwol.get_auth_token(
            auth_provider=env.get_remote_info().authProvider,
            authentication=env.get_authentication_info(),
            context=context
        )

    @staticmethod
    async def get_auth_token(
            auth_provider: AuthorizationProvider,
            authentication: Authentication,
            context: Context):

        if isinstance(authentication, DirectAuth):
            return await JwtProviderPyYouwol.get_auth_token_direct(
                auth_provider=auth_provider,
                authentication=authentication,
                context=context
            )

        if isinstance(authentication, BrowserAuth):
            return await JwtProviderPyYouwol.get_auth_token_cookie(
                auth_provider=auth_provider,
                context=context
            )

        raise RuntimeError("Authorization mode not managed")

    @staticmethod
    async def get_auth_token_direct(auth_provider: AuthorizationProvider, authentication: DirectAuth, context: Context):

        username = authentication.userName
        dependencies = {"username": username, "openIdClient": f"{auth_provider.openidClient}", "type": "auth_token"}

        cached_token = next((c for c in JwtProviderPyYouwol.__tokens_cache if c.is_valid(dependencies)), None)
        if cached_token:
            return cached_token.value

        try:
            token = await OidcConfig(auth_provider.openidBaseUrl).for_client(auth_provider.openidClient).direct_flow(
                username=username,
                password=authentication.password
            )
            access_token = token['access_token']
            expire = token['expires_in']
        except Exception as e:
            raise RuntimeError(f"Can not get access token for user '{username}' : {e}")

        deadline = datetime.timestamp(datetime.now()) + expire
        JwtProviderPyYouwol.__tokens_cache.append(DeadlinedCache(value=access_token, deadline=deadline,
                                                                 dependencies=dependencies))

        await context.info(text="Access token renewed",
                           data={"openIdClient": auth_provider.openidClient, "access_token": access_token})
        return access_token

    @staticmethod
    async def get_auth_token_cookie(auth_provider: AuthorizationProvider, context: Context):
        jwt_cache: CacheClient = JwtProviderPyYouwol.__jwt_cache
        request = context.request
        return await JwtProviderCookie(
            jwt_cache=jwt_cache,
            openid_infos=OidcInfos(
                base_uri=auth_provider.openidBaseUrl,
                client=auth_provider.openidClient
            )
        ).get_token(request, context)


async def get_remote_openid_infos(env: YouwolEnvironment) -> OidcInfos:
    return OidcInfos(base_uri=env.get_remote_info().authProvider.openidBaseUrl,
                     client=env.get_remote_info().authProvider.openidClient)
