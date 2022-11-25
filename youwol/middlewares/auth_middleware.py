from typing import Optional

from starlette.requests import Request

from youwol.environment.youwol_environment import yw_config
from youwol_utils import CacheClient
from youwol_utils.clients.oidc.oidc_config import OidcInfos
from youwol_utils.context import Context
from youwol_utils.middlewares import JwtProvider, JwtProviderCookie


class JwtProviderConfig(JwtProvider):

    def __init__(self, jwt_cache: CacheClient):
        self.__jwt_cache = jwt_cache

    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        config = await yw_config()
        if config.currentAccess.userId:
            return await config.get_auth_token(context=context)
        else:
            return await JwtProviderCookie(
                jwt_cache=self.__jwt_cache,
                openid_infos=OidcInfos(
                    base_uri=config.get_remote_info().openidBaseUrl,
                    client=config.get_remote_info().openidClient
                )
            ).get_token(request, context)


async def get_remote_openid_infos() -> OidcInfos:
    config = await yw_config()
    return OidcInfos(base_uri=config.get_remote_info().openidBaseUrl, client=config.get_remote_info().openidClient)
