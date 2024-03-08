# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.accounts import Configuration, get_router
from youwol.backends.common import BackendDeployment
from youwol.backends.common.app import get_fastapi_app
from youwol.backends.common.use_auth_middleware_with_cookie import (
    auth_cache,
    get_auth_middleware_with_cookie,
    tokens_storage,
)
from youwol.backends.common.use_keycloak_admin import (
    KEYCLOAK_ADMIN_BASE_URL,
    KEYCLOAK_ADMIN_CLIENT,
)
from youwol.backends.common.use_openid_client import oidc_client

# Youwol utilities
from youwol.utils.servers.fast_api import FastApiMiddleware


class AccountsDeployment(BackendDeployment):
    def router(self) -> APIRouter:
        return get_router(
            Configuration(
                openid_client=oidc_client,
                keycloak_admin_client=KEYCLOAK_ADMIN_CLIENT,
                keycloak_admin_base_url=KEYCLOAK_ADMIN_BASE_URL,
                auth_cache=auth_cache,
                tokens_storage=tokens_storage,
            )
        )

    def prefix(self) -> str:
        return "/api/accounts"

    def name(self) -> str:
        return "accounts"

    def middlewares(self) -> list[FastApiMiddleware]:
        return [
            get_auth_middleware_with_cookie(public_path="/api/accounts/openid_rp/"),
        ]


app = get_fastapi_app(AccountsDeployment())
