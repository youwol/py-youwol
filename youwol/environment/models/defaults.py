from pathlib import Path

from youwol_utils.clients.oidc.oidc_config import PublicClient

"""
Changing values defined in this file usually required updates in the documentation of models_config.
"""

default_http_port: int = 2000
default_platform_host: str = "platform.youwol.com"
default_openid_client_id: str = "public-dev"
default_path_data_dir: Path = Path("./databases")
default_path_cache_dir: Path = Path("./system")
default_path_projects_dir: Path = Path("Projects")
default_port_range_start: int = 3000
default_port_range_end: int = 4000
default_jwt_source: str = 'config'


def default_auth_provider(platform_host=default_platform_host):
    return {
        "openidBaseUrl": f"https://{platform_host}/auth/realms/youwol",
        "openidClient": PublicClient(client_id="tbd_test_openid_connect_js"),
        "keycloakAdminBaseUrl": f"https://{platform_host}/auth/admin/realms/youwol",
        "keycloakAdminClient": None
    }

