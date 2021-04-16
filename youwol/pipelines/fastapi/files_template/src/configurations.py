import argparse
from dataclasses import dataclass

from youwol_utils.assets_gateway import AssetsGatewayClient


parser = argparse.ArgumentParser()

parser.add_argument('--conf', help='name of the configuration.')
parser.add_argument('--port', help='port to listen, default to 8080')
parser.add_argument('--gateway', help='gateway url, default to ''(http://)')

args = parser.parse_args()
conf_name = args.conf or '{{conf}}'
port = args.port or '{{port}}'
gateway = args.gateway or '{{gateway}}'


@dataclass(frozen=True)
class Configuration:
    base_path = ""
    assets_client: AssetsGatewayClient
    port: int = int(port)


async def get_deployed_config() -> Configuration:

    return Configuration(
        assets_client=AssetsGatewayClient(
            url_base="http://assets-gateway")
        )


async def get_local_config() -> Configuration:
    return Configuration(
        assets_client=AssetsGatewayClient(
            url_base=f"{gateway}/api/assets-gateway")
        )

configurations = {
    'deployed': get_deployed_config,
    'local':  get_local_config
    }

current_configuration = None


async def get_configuration():

    global current_configuration
    if current_configuration:
        return current_configuration

    current_configuration = await configurations[conf_name]()
    return current_configuration
