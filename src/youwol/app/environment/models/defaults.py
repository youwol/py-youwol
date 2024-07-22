"""
This file gathers most of the non-trivial defaults values of the
:class:`configuration <youwol.app.environment.models.models_config.Configuration>`.
"""

# standard library
import os

from pathlib import Path

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
:attr:`LocalEnvironment.dataDir <youwol.app.environment.models.models_config.LocalEnvironment.dataDir>`
"""

default_path_cache_dir: Path = Path("./system")
"""
Default path used in
:attr:`LocalEnvironment.cacheDir <youwol.app.environment.models.models_config.LocalEnvironment.cacheDir>`
"""

default_path_projects_dir: Path = Path("Projects") / Path("youwol")
"""
Default path used in
:attr:`youwol.app.environment.models.models_project.ProjectsFinder.fromPath`.
"""

default_path_tokens_storage: Path = Path("./tokens_storage.json")
"""
Default path used in
:attr:`TokensStoragePath.path <youwol.app.environment.models.models_token_storage.TokensStoragePath.path>`
"""


default_path_tokens_storage_encrypted: Path = Path("./tokens_storage.json.encrypted")
"""
Default path used in
:attr:`youwol.app.environment.models.models_token_storage.TokensStorageSystemKeyring.path`.
"""

default_port_range_start: int = 3000
default_port_range_end: int = 4000
default_jwt_source: str = "config"
default_ignored_paths: list[str] = [
    "**/dist",
    "**/py-youwol/src",
    "**/node_modules",
    "**/.template",
    "**/.venv",
]
"""
Default path used in
:attr:`youwol.app.environment.models.models_project.ProjectsFinder.lookUpIgnore`.
"""


def default_auth_provider(platform_host: str = default_platform_host) -> JSON:
    """
    Return an :attr:`authProvider <youwol.app.environment.models.model_remote.CloudEnvironment.authProvider>`
    specification associated to a KeyCloak accounts manager.

    Parameters:
        platform_host: platform host (e.g. `platform.youwol.com`)

    Return:
        The authentication provider configuration
    """
    return {
        "openidBaseUrl": f"https://{platform_host}/auth/realms/youwol",
        "openidClient": PublicClient(client_id=default_openid_client_id),
    }
