# standard library
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


@dataclass(frozen=True)
class Configuration:
    """
    Configuration of the service.
    """

    assets_gtw_client: AssetsGatewayClient
    """
    Assets gateway client.
    """


class Dependencies:
    get_configuration: Callable[[], Configuration | Awaitable[Configuration]]


async def get_configuration() -> Configuration:
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
