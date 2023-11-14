# standard library
import os

from pathlib import Path

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import PublicClient

# Changing values defined in this file usually required updates in the documentation of models_config.

default_http_port: int = 2000
default_platform_host: str = (
    os.getenv("PY_YOUWOL_REMOTE")
    if os.getenv("PY_YOUWOL_REMOTE")
    else "platform.youwol.com"
)

default_openid_client_id: str = "tbd_test_openid_connect_js"
default_path_data_dir: Path = Path("./databases")
default_path_cache_dir: Path = Path("./system")
default_path_projects_dir: Path = Path("Projects") / Path("youwol")
default_path_tokens_storage: Path = Path("./tokens_storage.json")
default_path_tokens_storage_encrypted: Path = Path("./tokens_storage.json.encrypted")
default_port_range_start: int = 3000
default_port_range_end: int = 4000
default_jwt_source: str = "config"
default_ignored_paths = ["**/dist", "**/py-youwol", "**/node_modules", "**/.template"]


def default_auth_provider(platform_host=default_platform_host):
    return {
        "openidBaseUrl": f"https://{platform_host}/auth/realms/youwol",
        "openidClient": PublicClient(client_id=default_openid_client_id),
        "keycloakAdminBaseUrl": f"https://{platform_host}/auth/admin/realms/youwol",
        "keycloakAdminClient": None,
    }
