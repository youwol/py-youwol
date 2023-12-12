# third parties
import aiohttp

# Youwol utilities
from youwol.utils import AioHttpExecutor, CdnClient
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


def request_executor():
    return AioHttpExecutor(
        client_session=lambda: aiohttp.ClientSession(auto_decompress=False)
    )


cdn_client = CdnClient(
    url_base="http://cdn/api/cdn", request_executor=request_executor()
)
assets_gateway_client = AssetsGatewayClient(
    url_base="http://assets-gateway/api/assets-gateway",
    request_executor=request_executor(),
)
