
from youwol.web_socket import AdminContextLogger
from dataclasses import dataclass
from typing import Union

import youwol_cdn_backend as cdn
import youwol_assets_gateway as assets_gtw
from youwol_utils import TableBody, CdnClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.data_api.data import DataClient
from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.storage.storage import StorageClient as Storage
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import ContextLogger

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment


@dataclass(frozen=True)
class ServiceConfiguration:

    storage: Union[Storage, LocalStorage, None]
    doc_db: Union[DocDb, LocalDocDb, None]
    ctx_logger: ContextLogger


def get_service_configuration_local(
        env: YouwolEnvironment,
        namespace: str,
        table_body: TableBody
):

    return ServiceConfiguration(
        storage=LocalStorage(root_path=env.pathsBook.local_storage, bucket_name=namespace),
        doc_db=LocalDocDb(root_path=env.pathsBook.local_docdb,
                          keyspace_name=namespace,
                          table_body=table_body),
        ctx_logger=AdminContextLogger()
    )


async def get_cdn_config():
    env = await yw_config()
    return get_service_configuration_local(
        env=env,
        namespace=cdn.Constants.namespace,
        table_body=cdn.Constants.schema_docdb,
    )


async def get_assets_gtw_config():

    env = await yw_config()
    service_base_data = get_service_configuration_local(
        env=env,
        namespace='data',
        table_body=assets_gtw.Constants.table_data_schema,
    )
    url_base = f"http://localhost:{env.httpPort}/api"

    config_yw_assets_gateway = assets_gtw.Configuration(
        data_client=DataClient(storage=service_base_data.storage, docdb=service_base_data.doc_db),
        flux_client=FluxClient(url_base=f"{url_base}/flux-backend"),
        cdn_client=CdnClient(url_base=f"{url_base}/cdn-backend"),
        stories_client=StoriesClient(url_base=f"{url_base}/stories-backend"),
        treedb_client=TreeDbClient(url_base=f"{url_base}/treedb-backend"),
        assets_client=AssetsClient(url_base=f"{url_base}/assets-backend")
    )

    return config_yw_assets_gateway
