# Youwol utilities
from youwol.utils import CdnClient
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient

cdn_client = CdnClient(url_base="http://cdn/api/cdn")
assets_gateway_client = AssetsGatewayClient(
    url_base="http://assets-gateway/api/assets-gateway"
)
