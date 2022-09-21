from youwol.environment.forward_declaration import YouwolEnvironment
from youwol_utils import CdnClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.cdn_sessions_storage import CdnSessionsStorageClient
from youwol_utils.clients.files import FilesClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import Context


class RemoteClients:

    @staticmethod
    async def get_assets_gateway_client(remote_host: str, context: Context) -> AssetsGatewayClient:
        env = await context.get('env', YouwolEnvironment)
        remote_host = remote_host or env.get_remote_info().host
        auth_token = await env.get_auth_token(context=context, remote_host=remote_host)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return AssetsGatewayClient(url_base=f"https://{remote_host}/api/assets-gateway", headers=headers)


class LocalClients:

    @staticmethod
    def base_path(env: YouwolEnvironment):
        return f"http://localhost:{env.httpPort}/api"

    @staticmethod
    def get_assets_gateway_client(env: YouwolEnvironment) -> AssetsGatewayClient:
        base_path = LocalClients.base_path(env)
        return AssetsGatewayClient(url_base=f"{base_path}/assets-gateway")

    @staticmethod
    def get_assets_client(env: YouwolEnvironment) -> AssetsClient:
        base_path = LocalClients.base_path(env)
        return AssetsClient(url_base=f"{base_path}/assets-backend")

    @staticmethod
    def get_gtw_assets_client(env: YouwolEnvironment) -> AssetsClient:
        base_path = LocalClients.base_path(env)
        return AssetsClient(url_base=f"{base_path}/assets-gateway/assets-backend")

    @staticmethod
    def get_files_client(env: YouwolEnvironment) -> FilesClient:
        base_path = LocalClients.base_path(env)
        return FilesClient(url_base=f"{base_path}/files-backend")

    @staticmethod
    def get_gtw_files_client(env: YouwolEnvironment) -> FilesClient:
        base_path = LocalClients.base_path(env)
        return FilesClient(url_base=f"{base_path}/assets-gateway/files-backend")

    @staticmethod
    def get_treedb_client(env: YouwolEnvironment) -> TreeDbClient:
        base_path = LocalClients.base_path(env)
        return TreeDbClient(url_base=f"{base_path}/treedb-backend")

    @staticmethod
    def get_gtw_treedb_client(env: YouwolEnvironment) -> TreeDbClient:
        base_path = LocalClients.base_path(env)
        return TreeDbClient(url_base=f"{base_path}/assets-gateway/treedb-backend")

    @staticmethod
    def get_flux_client(env: YouwolEnvironment) -> FluxClient:
        base_path = LocalClients.base_path(env)
        return FluxClient(url_base=f"{base_path}/flux-backend")

    @staticmethod
    def get_cdn_client(env: YouwolEnvironment) -> CdnClient:
        base_path = LocalClients.base_path(env)
        return CdnClient(url_base=f"{base_path}/cdn-backend")

    @staticmethod
    def get_gtw_cdn_client(env: YouwolEnvironment) -> CdnClient:
        base_path = LocalClients.base_path(env)
        return CdnClient(url_base=f"{base_path}/assets-gateway/cdn-backend")

    @staticmethod
    def get_stories_client(env: YouwolEnvironment) -> StoriesClient:
        base_path = LocalClients.base_path(env)
        return StoriesClient(url_base=f"{base_path}/stories-backend")

    @staticmethod
    def get_cdn_sessions_storage_client(env: YouwolEnvironment) -> CdnSessionsStorageClient:
        base_path = LocalClients.base_path(env)
        return CdnSessionsStorageClient(url_base=f"{base_path}/cdn-sessions-storage")
