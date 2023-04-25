# typing
from typing import Awaitable, Callable, Optional, Union

# Youwol utilities
from youwol.utils.clients.cache import CacheClient
from youwol.utils.clients.oidc.oidc_config import PrivateClient, PublicClient


class Configuration:
    openid_base_url: str
    openid_client: Union[PrivateClient, PublicClient]
    keycloak_admin_base_url: Optional[str]
    admin_client: Optional[PrivateClient]
    jwt_cache: CacheClient
    pkce_cache: CacheClient
    secure_cookies: bool

    def __init__(
        self,
        openid_base_url: str,
        openid_client,
        keycloak_admin_base_url,
        admin_client,
        jwt_cache,
        pkce_cache,
        secure_cookies=True,
    ):
        self.openid_base_url = openid_base_url
        self.openid_client = openid_client
        self.keycloak_admin_base_url = keycloak_admin_base_url
        self.admin_client = admin_client
        self.jwt_cache = jwt_cache
        self.pkce_cache = pkce_cache
        self.secure_cookies = secure_cookies


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()

    if isinstance(conf, Configuration):
        return conf
    else:
        return await conf
