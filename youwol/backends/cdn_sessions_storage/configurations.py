from dataclasses import dataclass
from typing import Optional, Callable

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol_utils import LocalStorageClient


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolEnvironment
    open_api_prefix: str
    base_path: str

    storage: LocalStorageClient
    admin_headers = None

    namespace: str = "cdn-sessions-storage"
    default_owner: str = "/youwol-users"
    cache_prefix: str = "cdn-sessions-storage_"
    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"


config_yw_cdn_sessions_server: Optional[Configuration] = None


async def get_configuration(config_yw=None):

    global config_yw_cdn_sessions_server
    if not config_yw:
        config_yw = await yw_config()

    if config_yw_cdn_sessions_server and config_yw_cdn_sessions_server.yw_config == config_yw:
        return config_yw_cdn_sessions_server

    storage = LocalStorageClient(root_path=config_yw.pathsBook.local_storage,
                                 bucket_name=Configuration.namespace)

    config_yw_cdn_sessions_server = Configuration(
        yw_config=config_yw,
        open_api_prefix='',
        base_path="/api/cdn-backend",
        storage=storage
        )

    return config_yw_cdn_sessions_server
