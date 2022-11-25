from pathlib import Path

from youwol_utils.clients.oidc.oidc_config import PublicClient

default_http_port: int = 2000
default_platform_host: str = "platform.youwol.com"
default_openid_client_id: str = "public-dev"
default_path_data_dir: Path = Path("databases")
default_path_cache_dir: Path = Path("system")
default_path_projects_dir: Path = Path("Projects")
default_port_range_start: int = 3000
default_port_range_end: int = 4000
default_jwt_source: str = 'config'


def default_cloud_environment(platform_host):
    return {
        "host": platform_host,
        "name": platform_host,
        "openidBaseUrl": f"https://{platform_host}/auth/realms/youwol",
        "openidClient": PublicClient(client_id="tbd_test_openid_connect_js"),
        "keycloakAdminBaseUrl": f"https://{platform_host}/auth/admin/realms/youwol",
        "keycloakAdminClient": None
    }

