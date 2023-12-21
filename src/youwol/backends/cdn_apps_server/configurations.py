# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Callable, Union

# Youwol utilities
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


@dataclass(frozen=True)
class Configuration:
    assets_gtw_client: AssetsGatewayClient


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration() -> Configuration:
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
