from typing import Callable, cast, Any, Optional

from dataclasses import dataclass

from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from .raw_stores.story import StoriesStore
from .raw_stores.data import DataStore
from .raw_stores.drive_pack import DrivePackStore
from .raw_stores.group_showcase import GroupShowCaseStore
from .raw_stores.package import PackagesStore
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils import (
    CdnClient, DocDb, Storage, LocalDocDbClient, LocalStorageClient, TableBody
    )
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.clients.data_api.data import (
    DataClient, FILES_TABLE
    )
from youwol_utils.clients.flux.flux import FluxClient
from .raw_stores.flux_project import FluxProjectsStore

from youwol.configuration.youwol_configuration import yw_config, YouwolConfiguration
from youwol.configurations import api_configuration as py_yw_config


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolConfiguration
    open_api_prefix: str
    base_path: str

    data_client: DataClient
    flux_client: FluxClient
    cdn_client: CdnClient
    stories_client: StoriesClient
    treedb_client: TreeDbClient
    assets_client: AssetsClient
    assets_gtw_client: AssetsGatewayClient

    docdb_factory: Callable[[str, str, str], DocDb]
    storage_factory: Callable[[str], Storage]

    replication_factor: int = 2
    to_package = ["flux-project", "data", "package", "group-showcase"]

    def assets_stores(self):
        return [
            FluxProjectsStore(client=self.flux_client),
            PackagesStore(client=self.cdn_client),
            GroupShowCaseStore(client=None),
            DataStore(client=self.data_client),
            StoriesStore(client=self.stories_client),
            DrivePackStore(client=self.data_client)
            ]


config_yw_assets_gateway: Optional[Configuration] = None


async def get_configuration(config_yw=None):

    global config_yw_assets_gateway
    if not config_yw:
        config_yw = await yw_config()

    if config_yw_assets_gateway and config_yw_assets_gateway.yw_config == config_yw:
        return config_yw_assets_gateway

    storage = LocalStorageClient(root_path=config_yw.pathsBook.local_storage, bucket_name='data')
    docdb = LocalDocDbClient(root_path=config_yw.pathsBook.local_docdb,
                             keyspace_name='data',
                             table_body=FILES_TABLE
                             )

    data_client = DataClient(storage=cast(Any, storage), docdb=cast(Any, docdb))
    flux_client = FluxClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/flux-backend")
    cdn_client = CdnClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/cdn-backend")
    stories_client = StoriesClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/stories-backend")
    treedb_client = TreeDbClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/treedb-backend")
    assets_client = AssetsClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/assets-backend")
    assets_gtw_client = AssetsGatewayClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/assets-gateway")

    def docdb_factory(keyspace: str, table: str, primary: str):
        return LocalDocDbClient(root_path=config_yw.pathsBook.local_docdb, keyspace_name=keyspace,
                                table_body=TableBody(name=table, columns=[], partition_key=[primary], version="0.0"),
                                )

    def storage_factory(bucket_name: str):
        return LocalStorageClient(root_path=config_yw.pathsBook.local_storage,
                                  bucket_name=bucket_name)

    config_yw_assets_gateway = Configuration(
        yw_config=config_yw,
        open_api_prefix='',
        base_path="/api/assets-gateway",
        data_client=data_client,
        flux_client=flux_client,
        cdn_client=cdn_client,
        stories_client=stories_client,
        treedb_client=treedb_client,
        assets_client=assets_client,
        docdb_factory=docdb_factory,
        storage_factory=storage_factory,
        assets_gtw_client=assets_gtw_client
        )

    return config_yw_assets_gateway
