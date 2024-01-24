# standard library
import os

from pathlib import Path

# typing
from typing import List

# Youwol utilities
from youwol.utils import JSON
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
"""
Default path used in
[LocalEnvironment.dataDir](@yw-nav-attr:youwol.app.environment.models.models_config.LocalEnvironment)
"""

default_path_cache_dir: Path = Path("./system")
"""
Default path used in
[LocalEnvironment.cacheDir](@yw-nav-attr:youwol.app.environment.models.models_config.LocalEnvironment.cacheDir)
"""

default_path_projects_dir: Path = Path("Projects") / Path("youwol")
"""
Default path used in
<a href="@yw-nav-attr:youwol.app.environment.models.models_config.RecursiveProjectsFinder.fromPaths">
RecursiveProjectsFinder.fromPaths</a>
"""

default_path_tokens_storage: Path = Path("./tokens_storage.json")
"""
Default path used in
[TokensStoragePath.path](@yw-nav-attr:youwol.app.environment.models.models_config.TokensStoragePath.path)
"""


default_path_tokens_storage_encrypted: Path = Path("./tokens_storage.json.encrypted")
"""
Default path used in
<a href="@yw-nav-attr:youwol.app.environment.models.models_config.TokensStorageSystemKeyring.path">
TokensStorageSystemKeyring.path</a>>
"""

default_port_range_start: int = 3000
default_port_range_end: int = 4000
default_jwt_source: str = "config"
default_ignored_paths: List[str] = [
    "**/dist",
    "**/py-youwol/src",
    "**/node_modules",
    "**/.template",
]
"""
Default path used in
<a href="@yw-nav-attr:youwol.app.environment.models.models_config.RecursiveProjectsFinder.ignoredPatterns">
RecursiveProjectsFinder.ignoredPatterns></a>.
"""


def default_auth_provider(platform_host: str = default_platform_host) -> JSON:
    """
    Return an [authProvider](@yw-nav-attr:youwol.app.environment.models.models_config.CloudEnvironment.authProvider)
    specification associated to a KeyCloak accounts manager.

    Parameters:
        platform_host: platform host (e.g. `platform.youwol.com`)

    Return:
        The authentication provider configuration
    """
    return {
        "openidBaseUrl": f"https://{platform_host}/auth/realms/youwol",
        "openidClient": PublicClient(client_id=default_openid_client_id),
        "keycloakAdminBaseUrl": f"https://{platform_host}/auth/admin/realms/youwol",
        "keycloakAdminClient": None,
    }
