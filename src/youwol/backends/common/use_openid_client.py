# standard library
import os

# Youwol backends
from youwol.backends.common.use_openid_base_url import openid_base_url

# Youwol utilities
from youwol.utils import OidcConfig, PrivateClient
from youwol.utils.servers.env import OPENID_CLIENT, Env

required_env_vars = OPENID_CLIENT

not_founds = [v for v in required_env_vars if not os.getenv(v.value)]
if not_founds:
    raise RuntimeError(f"Missing environments variable: {not_founds}")
oidc_config = OidcConfig(openid_base_url)
openid_client_id = os.getenv(Env.OPENID_CLIENT_ID.value)
openid_client_secret = os.getenv(Env.OPENID_CLIENT_SECRET.value)
oidc_client = oidc_config.for_client(
    client=PrivateClient(
        client_id=openid_client_id, client_secret=openid_client_secret
    ),
)
