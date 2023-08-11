# standard library
import uuid

# typing
from typing import Awaitable, Callable, Optional, Union

# Youwol utilities
from youwol.utils.clients.cache import CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient
from youwol.utils.clients.oidc.tokens_manager import TokensManager, TokensStorage
from youwol.utils.clients.oidc.users_management import KeycloakUsersManagement

# relative
from .openid_rp.openid_flows_service import OpenidFlowsService


def default_tokens_id_generator() -> str:
    return str(uuid.uuid4())


class Configuration:
    def __init__(
        self,
        openid_base_url: str,
        openid_client: OidcForClient,
        tokens_storage: TokensStorage,
        auth_cache: CacheClient,
        keycloak_admin_base_url: Optional[str],
        keycloak_admin_client: Optional[OidcForClient],
        https: bool = True,
        tokens_id_generator: Callable[[], str] = default_tokens_id_generator,
        logout_url: Optional[str] = None,
        account_manager_url: Optional[str] = None,
    ):
        self.oidc_client = openid_client
        self.keycloak_admin_client = keycloak_admin_client
        self.keycloak_users_management = (
            KeycloakUsersManagement(
                realm_url=keycloak_admin_base_url,
                cache=auth_cache,
                oidc_client=self.keycloak_admin_client,
            )
            if self.keycloak_admin_client is not None
            and keycloak_admin_base_url is not None
            else None
        )
        self.openid_flows = OpenidFlowsService(
            cache=auth_cache,
            tokens_storage=tokens_storage,
            oidc_client=self.oidc_client,
            tokens_id_generator=tokens_id_generator,
        )
        self.tokens_manager = TokensManager(
            storage=tokens_storage, oidc_client=self.oidc_client
        )
        self.https = https
        self.logout_url = logout_url
        self.account_manager_url = account_manager_url
        self.keycloak_base_url = openid_base_url


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration() -> Configuration:
    conf = Dependencies.get_configuration()

    if isinstance(conf, Configuration):
        return conf
    return await conf
