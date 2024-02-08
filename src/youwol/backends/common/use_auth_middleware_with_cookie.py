# standard library
import os

# third parties
from starlette.responses import Response

# Youwol backends
from youwol.backends.common.env import get_not_empty_env_value
from youwol.backends.common.use_auth_middleware import jwt_provider_bearer
from youwol.backends.common.use_openid_base_url import openid_base_url
from youwol.backends.common.use_openid_client import oidc_client

# Youwol utilities
from youwol.utils import RedisCacheClient
from youwol.utils.clients.oidc.tokens_manager import TokensManager, TokensStorageCache
from youwol.utils.middlewares import (
    AuthMiddleware,
    JwtProviderCookie,
    redirect_to_login,
)
from youwol.utils.servers.env import REDIS, Env
from youwol.utils.servers.fast_api import FastApiMiddleware

required_env_vars = REDIS

not_founds = [v for v in required_env_vars if not os.getenv(v.value)]
if not_founds:
    raise RuntimeError(f"Missing environments variable: {not_founds}")
redis_host = get_not_empty_env_value(Env.REDIS_HOST)
auth_cache = RedisCacheClient(host=redis_host, prefix="auth_cache")

tokens_storage = TokensStorageCache(cache=auth_cache)


def get_auth_middleware_with_cookie(
    public_path: str | None = None,
    redirect_to_login_for_path: str | None = None,
) -> FastApiMiddleware:
    auth_middleware_args = {
        "jwt_providers": [
            jwt_provider_bearer,
            JwtProviderCookie(
                TokensManager(storage=tokens_storage, oidc_client=oidc_client),
                openid_base_url=openid_base_url,
            ),
        ],
        "predicate_public_path": lambda url: url.path.startswith("/observability")
        or (public_path and url.path.startswith(public_path)),
    }

    if redirect_to_login_for_path:
        auth_middleware_args["on_missing_token"] = lambda url, text: (
            redirect_to_login(url)
            if url.path.startswith(redirect_to_login_for_path)
            else Response(content=f"Authentication failure : {text}", status_code=403)
        )

    return FastApiMiddleware(AuthMiddleware, args=auth_middleware_args)
