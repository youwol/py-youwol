# standard library
import uuid

# typing
from typing import Awaitable, Callable, Optional, Union

# Youwol utilities
from youwol.utils.clients.cache import CacheClient
from youwol.utils.clients.oidc.oidc_config import (
    OidcConfig,
    OidcForClient,
    PrivateClient,
    PublicClient,
)
from youwol.utils.clients.oidc.tokens_manager import TokensManager
from youwol.utils.clients.oidc.users_management import KeycloakUsersManagement

# relative
from .openid_rp.openid_flows_service import OpenidFlowsService


def default_tokens_id_generator() -> str:
    return str(uuid.uuid4())


class Configuration:
    oidc_client: OidcForClient
    oidc_admin_client: Optional[OidcForClient]
    keycloak_users_management: Optional[KeycloakUsersManagement]
    openid_flows: OpenidFlowsService
    tokens_manager: TokensManager
    https: bool

    def __init__(
        self,
        openid_base_url: str,
        openid_client: Union[PrivateClient, PublicClient],
        keycloak_admin_base_url: str,
        admin_client: Optional[PrivateClient],
        auth_cache: CacheClient,
        https: bool = True,
        tokens_id_generator: Callable[[], str] = default_tokens_id_generator,
    ):
        self.oidc_client = OidcConfig(openid_base_url).for_client(openid_client)
        self.oidc_admin_client = (
            OidcConfig(openid_base_url).for_client(admin_client)
            if admin_client is not None
            else None
        )
        self.keycloak_users_management = (
            KeycloakUsersManagement(
                realm_url=keycloak_admin_base_url,
                cache=auth_cache,
                oidc_client=self.oidc_admin_client,
            )
            if self.oidc_admin_client is not None
            and keycloak_admin_base_url is not None
            else None
        )
        self.openid_flows = OpenidFlowsService(
            cache=auth_cache,
            oidc_client=self.oidc_client,
            tokens_id_generator=tokens_id_generator,
        )
        self.tokens_manager = TokensManager(
            cache=auth_cache, oidc_client=self.oidc_client
        )
        self.https = https


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration() -> Configuration:
    conf = Dependencies.get_configuration()

    if isinstance(conf, Configuration):
        return conf
    return await conf
