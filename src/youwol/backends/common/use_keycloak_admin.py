# standard library
import os

# Youwol backends
from youwol.backends.common.use_openid_client import oidc_config

# Youwol utilities
from youwol.utils import PrivateClient
from youwol.utils.servers.env import KEYCLOAK_ADMIN, Env

keycloak_admin_base_url = None
keycloak_admin_client = None

has_keycloak_admin = [v for v in KEYCLOAK_ADMIN if os.getenv(v.value)]
if has_keycloak_admin:
    keycloak_admin_client_id = os.getenv(Env.KEYCLOAK_ADMIN_CLIENT_ID.value)
    keycloak_admin_client_secret = os.getenv(Env.KEYCLOAK_ADMIN_CLIENT_SECRET.value)
    keycloak_admin_base_url = os.getenv(Env.KEYCLOAK_ADMIN_BASE_URL.value)
    keycloak_admin_client = oidc_config.for_client(
        PrivateClient(
            client_id=keycloak_admin_client_id,
            client_secret=keycloak_admin_client_secret,
        )
    )
else:
    print("No Keycloak administration")
