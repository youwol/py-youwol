# standard library
import uuid

# typing
from typing import Awaitable, Callable, Optional, Union

# Youwol utilities
from youwol.utils.clients.cache import CacheClient
from youwol.utils.clients.oidc.oidc_config import (
    OidcConfig,
    PrivateClient,
    PublicClient,
)

# relative
from .openid_rp.openid_flows_service import OpenidFlowsService


class Configuration:
    openid_base_url: str
    openid_client: Union[PrivateClient, PublicClient]
    keycloak_admin_base_url: Optional[str]
    admin_client: Optional[PrivateClient]
    auth_cache: CacheClient
    secure_cookies: bool
    authorization: OpenidFlowsService

    def __init__(
        self,
        openid_base_url: str,
        openid_client,
        keycloak_admin_base_url,
        admin_client,
        auth_cache,
        secure_cookies=True,
        tokens_id_generator: Callable[[], str] = (
            lambda: default_tokens_id_generator()
        ),
    ):
        self.openid_base_url = openid_base_url
        self.openid_client = openid_client
        self.keycloak_admin_base_url = keycloak_admin_base_url
        self.admin_client = admin_client
        self.auth_cache = auth_cache
        self.secure_cookies = secure_cookies
        self.authorization = OpenidFlowsService(
            cache=self.auth_cache,
            oidc_client=OidcConfig(base_url=self.openid_base_url).for_client(
                client=self.openid_client
            ),
            tokens_id_generator=tokens_id_generator,
        )


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()

    if isinstance(conf, Configuration):
        return conf
    else:
        return await conf


def default_tokens_id_generator() -> str:
    return str(uuid.uuid4())
