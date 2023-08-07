# standard library
import os

# typing
from typing import List

# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.accounts import Configuration, get_router
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app

# Youwol utilities
from youwol.utils import OidcConfig, PrivateClient, RedisCacheClient
from youwol.utils.clients.oidc.tokens_manager import TokensManager, TokensStorageCache
from youwol.utils.middlewares import (
    AuthMiddleware,
    JwtProviderBearer,
    JwtProviderCookie,
)
from youwol.utils.servers.env import KEYCLOAK_ADMIN, OPENID_CLIENT, REDIS, Env
from youwol.utils.servers.fast_api import FastApiMiddleware


class AccountsDeployment(BackendDeployment):
    def __init__(self):
        required_env_vars = OPENID_CLIENT + REDIS

        not_founds = [v for v in required_env_vars if not os.getenv(v)]
        if not_founds:
            raise RuntimeError(f"Missing environments variable: {not_founds}")

        openid_base_url = os.getenv(str(Env.OPENID_BASE_URL))
        oidc_config = OidcConfig(openid_base_url)
        has_keycloak_admin = [v for v in KEYCLOAK_ADMIN if os.getenv(v)]
        if has_keycloak_admin:
            keycloak_admin_client_id = os.getenv(str(Env.KEYCLOAK_ADMIN_CLIENT_ID))
            keycloak_admin_client_secret = os.getenv(
                str(Env.KEYCLOAK_ADMIN_CLIENT_SECRET)
            )
            keycloak_admin_base_url = os.getenv(str(Env.KEYCLOAK_ADMIN_BASE_URL))
            admin_client = oidc_config.for_client(
                PrivateClient(
                    client_id=keycloak_admin_client_id,
                    client_secret=keycloak_admin_client_secret,
                )
            )
        else:
            print("No Keycloak administration")
            keycloak_admin_base_url = None
            admin_client = None

        openid_client_id = os.getenv(str(Env.OPENID_CLIENT_ID))
        openid_client_secret = os.getenv(str(Env.OPENID_CLIENT_SECRET))
        oidc_client = oidc_config.for_client(
            client=PrivateClient(
                client_id=openid_client_id, client_secret=openid_client_secret
            ),
        )

        redis_host = os.getenv(str(Env.REDIS_HOST))
        auth_cache = RedisCacheClient(host=redis_host, prefix="auth_cache")

        tokens_storage = TokensStorageCache(cache=auth_cache)
        self.__config = Configuration(
            openid_client=oidc_client,
            openid_base_url=openid_base_url,
            admin_client=admin_client,
            keycloak_admin_base_url=keycloak_admin_base_url,
            auth_cache=auth_cache,
            tokens_storage=tokens_storage,
        )

        self.__middlewares = [
            FastApiMiddleware(
                AuthMiddleware,
                {
                    "predicate_public_path": lambda url: url.path.startswith(
                        "/observability"
                    )
                    or url.path.startswith("/api/accounts/openid_rp/"),
                    "jwt_providers": [
                        JwtProviderBearer(openid_base_url=openid_base_url),
                        JwtProviderCookie(
                            TokensManager(
                                storage=tokens_storage, oidc_client=oidc_client
                            ),
                            openid_base_url=openid_base_url,
                        ),
                    ],
                },
            )
        ]

    def router(self) -> APIRouter:
        return get_router(self.__config)

    def prefix(self) -> str:
        return "/api/accounts"

    def version(self) -> str:
        return "1.1.0"

    def name(self) -> str:
        return "accounts"

    def middlewares(self) -> List[FastApiMiddleware]:
        return self.__middlewares


app = get_fastapi_app(AccountsDeployment())
