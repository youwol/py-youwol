from dataclasses import dataclass
from typing import Union, Any, Coroutine, Dict, Optional

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolEnvironment
    open_api_prefix: str
    base_path: str

    gtw_client: AssetsGatewayClient

    admin_headers: Union[Coroutine[Any, Any, Dict[str, str]], None]


config_yw_cdn_apps_server: Optional[Configuration] = None


async def get_configuration(config_yw=None):

    global config_yw_cdn_apps_server
    if not config_yw:
        config_yw = await yw_config()

    if config_yw_cdn_apps_server and config_yw_cdn_apps_server.yw_config == config_yw:
        return config_yw_cdn_apps_server

    gtw_client = AssetsGatewayClient(url_base=f"http://localhost:{config_yw.httpPort}/api/assets-gateway")

    config_yw_cdn_apps_server = Configuration(
        yw_config=config_yw,
        open_api_prefix='',
        base_path="/api/cdn-backend",
        gtw_client=gtw_client,
        admin_headers=None
        )

    return config_yw_cdn_apps_server
