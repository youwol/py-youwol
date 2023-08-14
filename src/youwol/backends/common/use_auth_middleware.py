# Youwol backends
from youwol.backends.common.use_openid_base_url import openid_base_url

# Youwol utilities
from youwol.utils.middlewares import AuthMiddleware, JwtProviderBearer
from youwol.utils.servers.fast_api import FastApiMiddleware

jwt_provider_bearer = JwtProviderBearer(openid_base_url=openid_base_url)
auth_middleware = FastApiMiddleware(
    AuthMiddleware,
    {
        "predicate_public_path": lambda url: url.path.startswith("/observability"),
        "jwt_providers": [
            jwt_provider_bearer,
        ],
    },
)
