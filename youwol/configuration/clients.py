from context import Context
from typing import List
from youwol_utils import CdnClient, StorageClient, TableBody, SecondaryIndex, DocDbClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient


class RemoteClients:

    @staticmethod
    async def get_assets_gateway_client(context: Context) -> AssetsGatewayClient:

        remote_host = context.config.get_remote_info().host
        auth_token = await context.config.get_auth_token(context=context)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return AssetsGatewayClient(url_base=f"https://{remote_host}/api/assets-gateway", headers=headers)

    @staticmethod
    async def get_treedb_client(context: Context) -> TreeDbClient:

        remote_host = context.config.get_remote_info().host
        auth_token = await context.config.get_auth_token(context=context)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return TreeDbClient(url_base=f"https://{remote_host}/api/treedb-backend", headers=headers)

    @staticmethod
    async def get_flux_client(context: Context) -> FluxClient:
        # <!> this method will be removed as FluxClient should not be reachable
        remote_host = context.config.get_remote_info().host
        auth_token = await context.config.get_auth_token(context=context)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return FluxClient(url_base=f"https://{remote_host}/api/flux-backend", headers=headers)

    @staticmethod
    async def get_stories_client(context: Context) -> StoriesClient:
        # <!> this method will be removed as StoriesClient should not be reachable
        remote_host = context.config.get_remote_info().host
        auth_token = await context.config.get_auth_token(context=context)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return StoriesClient(url_base=f"https://{remote_host}/api/stories-backend", headers=headers)

    @staticmethod
    async def get_storage_client(bucket_name: str, context: Context) -> StorageClient:

        remote_host = context.config.get_remote_info().host
        auth_token = await context.config.get_auth_token(context=context)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return StorageClient(
            url_base=f"https://{remote_host}/api/storage",
            bucket_name=bucket_name,
            headers=headers
            )

    @staticmethod
    async def get_docdb_client(keyspace_name: str, table_body: TableBody, secondary_indexes: List[SecondaryIndex],
                               context: Context) -> DocDbClient:

        remote_host = context.config.get_remote_info().host
        auth_token = await context.config.get_auth_token(context=context)
        headers = {"Authorization": f"Bearer {auth_token}"}
        return DocDbClient(
            url_base=f"https://{remote_host}/api/docdb",
            table_body=table_body,
            secondary_indexes=secondary_indexes,
            keyspace_name=keyspace_name,
            replication_factor=2,
            headers=headers
            )


class LocalClients:

    @staticmethod
    def base_path(context: Context):
        return f"http://localhost:{context.config.http_port}/api"

    @staticmethod
    def get_assets_gateway_client(context: Context) -> AssetsGatewayClient:
        return AssetsGatewayClient(url_base=f"{LocalClients.base_path(context)}/assets-gateway")

    @staticmethod
    def get_assets_client(context: Context) -> AssetsClient:
        return AssetsClient(url_base=f"{LocalClients.base_path(context)}/assets-backend")

    @staticmethod
    def get_treedb_client(context: Context) -> TreeDbClient:
        return TreeDbClient(url_base=f"{LocalClients.base_path(context)}/treedb-backend")

    @staticmethod
    def get_flux_client(context: Context) -> FluxClient:
        return FluxClient(url_base=f"{LocalClients.base_path(context)}/flux-backend")

    @staticmethod
    def get_cdn_client(context: Context) -> CdnClient:
        return CdnClient(url_base=f"{LocalClients.base_path(context)}/cdn-backend")

    @staticmethod
    def get_stories_client(context: Context) -> StoriesClient:
        return StoriesClient(url_base=f"{LocalClients.base_path(context)}/stories-backend")
