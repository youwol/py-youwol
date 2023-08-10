# Youwol backends
from youwol.backends.common.use_openid_base_url import openid_base_url

# Youwol utilities
from youwol.utils.middlewares import JwtProviderBearer

jwt_provider_bearer = JwtProviderBearer(openid_base_url=openid_base_url)
