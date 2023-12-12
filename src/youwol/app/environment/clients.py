# third parties
import aiohttp

# Youwol utilities
from youwol.utils import AioHttpExecutor, CdnClient
from youwol.utils.clients.accounts.accounts import AccountsClient
from youwol.utils.clients.assets.assets import AssetsClient
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol.utils.clients.cdn_sessions_storage import CdnSessionsStorageClient
from youwol.utils.clients.files import FilesClient
from youwol.utils.clients.flux.flux import FluxClient
from youwol.utils.clients.stories.stories import StoriesClient
from youwol.utils.clients.treedb.treedb import TreeDbClient

# relative
from .youwol_environment import YouwolEnvironment


def client_session():
    return aiohttp.ClientSession(auto_decompress=False)


class RemoteClients:
    @staticmethod
    async def get_assets_gateway_client(remote_host: str) -> AssetsGatewayClient:
        return AssetsGatewayClient(url_base=f"https://{remote_host}/api/assets-gateway")


class LocalClients:
    request_executor = AioHttpExecutor(client_session=client_session)

    @staticmethod
    def base_path(env: YouwolEnvironment):
        return f"http://localhost:{env.httpPort}/api"

    @staticmethod
    def get_assets_gateway_client(env: YouwolEnvironment) -> AssetsGatewayClient:
        base_path = LocalClients.base_path(env)
        return AssetsGatewayClient(
            url_base=f"{base_path}/assets-gateway",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_assets_client(env: YouwolEnvironment) -> AssetsClient:
        base_path = LocalClients.base_path(env)
        return AssetsClient(
            url_base=f"{base_path}/assets-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_gtw_assets_client(env: YouwolEnvironment) -> AssetsClient:
        base_path = LocalClients.base_path(env)
        return AssetsClient(
            url_base=f"{base_path}/assets-gateway/assets-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_files_client(env: YouwolEnvironment) -> FilesClient:
        base_path = LocalClients.base_path(env)
        return FilesClient(
            url_base=f"{base_path}/files-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_gtw_files_client(env: YouwolEnvironment) -> FilesClient:
        base_path = LocalClients.base_path(env)
        return FilesClient(
            url_base=f"{base_path}/assets-gateway/files-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_treedb_client(env: YouwolEnvironment) -> TreeDbClient:
        base_path = LocalClients.base_path(env)
        return TreeDbClient(
            url_base=f"{base_path}/treedb-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_gtw_treedb_client(env: YouwolEnvironment) -> TreeDbClient:
        base_path = LocalClients.base_path(env)
        return TreeDbClient(
            url_base=f"{base_path}/assets-gateway/treedb-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_flux_client(env: YouwolEnvironment) -> FluxClient:
        base_path = LocalClients.base_path(env)
        return FluxClient(
            url_base=f"{base_path}/flux-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_cdn_client(env: YouwolEnvironment) -> CdnClient:
        base_path = LocalClients.base_path(env)
        return CdnClient(
            url_base=f"{base_path}/cdn-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_gtw_cdn_client(env: YouwolEnvironment) -> CdnClient:
        base_path = LocalClients.base_path(env)
        return CdnClient(
            url_base=f"{base_path}/assets-gateway/cdn-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_stories_client(env: YouwolEnvironment) -> StoriesClient:
        base_path = LocalClients.base_path(env)
        return StoriesClient(
            url_base=f"{base_path}/stories-backend",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_cdn_sessions_storage_client(
        env: YouwolEnvironment,
    ) -> CdnSessionsStorageClient:
        base_path = LocalClients.base_path(env)
        return CdnSessionsStorageClient(
            url_base=f"{base_path}/cdn-sessions-storage",
            request_executor=LocalClients.request_executor,
        )

    @staticmethod
    def get_accounts_client(env: YouwolEnvironment) -> AccountsClient:
        base_path = LocalClients.base_path(env)
        return AccountsClient(
            url_base=f"{base_path}/accounts",
            request_executor=LocalClients.request_executor,
        )
