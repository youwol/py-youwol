# standard library
import os

# Youwol backends
from youwol.backends.common.use_openid_client import oidc_config

# Youwol utilities
from youwol.utils import PrivateClient
from youwol.utils.servers.env import KEYCLOAK_ADMIN, Env

# relative
from .env import get_not_empty_env_value

keycloak_admin_base_url = None
keycloak_admin_client = None

has_keycloak_admin = [v for v in KEYCLOAK_ADMIN if os.getenv(v.value)]
if has_keycloak_admin:
    keycloak_admin_base_url = get_not_empty_env_value(Env.KEYCLOAK_ADMIN_BASE_URL)
    keycloak_admin_client = oidc_config.for_client(
        PrivateClient(
            client_id=(get_not_empty_env_value(Env.KEYCLOAK_ADMIN_CLIENT_ID)),
            client_secret=(get_not_empty_env_value(Env.KEYCLOAK_ADMIN_CLIENT_SECRET)),
        )
    )
else:
    print("No Keycloak administration")
