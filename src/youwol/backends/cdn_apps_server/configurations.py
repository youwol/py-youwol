# standard library
from dataclasses import dataclass

# typing
from typing import Awaitable, Callable

# Youwol utilities
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


@dataclass(frozen=True)
class Configuration:
    assets_gtw_client: AssetsGatewayClient


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration() -> Configuration:
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
