from youwol.environment.clients import LocalClients
from youwol.web_socket import AdminContextLogger
from dataclasses import dataclass
from typing import Union

import youwol_cdn_backend as cdn
import youwol_assets_gateway as assets_gtw
import youwol_stories_backend as stories
import youwol_cdn_apps_server as cdn_apps_server
import youwol_tree_db_backend as tree_db
import youwol_assets_backend as assets_backend
from youwol_stories_backend import Configuration as StoriesConfig
from youwol_utils import TableBody, CdnClient, LocalDocDbInMemoryClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.data_api.data import DataClient
from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb, LocalDocDbClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.storage.storage import StorageClient as Storage
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import ContextLogger

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol_utils.http_clients.assets_backend import ASSETS_TABLE, ACCESS_HISTORY, ACCESS_POLICY
from youwol_utils.http_clients.tree_db_backend import create_doc_dbs


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


async def cdn_config_py_youwol():
    env = await yw_config()
    return cdn.Configuration(
        storage=LocalStorage(
            root_path=env.pathsBook.local_storage,
            bucket_name=cdn.Constants.namespace
        ),
        doc_db=LocalDocDb(root_path=env.pathsBook.local_docdb,
                          keyspace_name=cdn.Constants.namespace,
                          table_body=cdn.Constants.schema_docdb)
    )


async def tree_db_config_py_youwol():
    env = await yw_config()
    doc_dbs = create_doc_dbs(
        factory_db=LocalDocDbClient,
        root_path=env.pathsBook.local_docdb
    )
    return tree_db.Configuration(
        doc_dbs=doc_dbs
    )


async def assets_backend_config_py_youwol():
    env = await yw_config()
    return assets_backend.Configuration(
        storage=LocalStorage(
            root_path=env.pathsBook.local_storage,
            bucket_name=assets_backend.Constants.namespace
        ),
        doc_db_asset=LocalDocDb(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=assets_backend.Constants.namespace,
            table_body=ASSETS_TABLE
        ),
        doc_db_access_history=LocalDocDbInMemoryClient(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=assets_backend.Constants.namespace,
            table_body=ACCESS_HISTORY
        ),
        doc_db_access_policy=LocalDocDbClient(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=assets_backend.Constants.namespace,
            table_body=ACCESS_POLICY
        )
    )


async def assets_gtw_config_py_youwol():

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


async def stories_config_py_youwol():

    env = await yw_config()
    storage = LocalStorage(
        root_path=env.pathsBook.local_storage,
        bucket_name=stories.Constants.namespace
    )

    doc_db_stories = LocalDocDb(
        root_path=env.pathsBook.local_docdb,
        keyspace_name=stories.Constants.namespace,
        table_body=stories.Constants.db_schema_stories
    )

    doc_db_documents = LocalDocDb(
        root_path=env.pathsBook.local_docdb,
        keyspace_name=stories.Constants.namespace,
        table_body=stories.Constants.db_schema_documents,
        secondary_indexes=[stories.Constants.db_schema_doc_by_id]
    )

    assets_gtw_client = LocalClients.get_assets_gateway_client(env=env)

    return StoriesConfig(
        storage=storage,
        doc_db_stories=doc_db_stories,
        doc_db_documents=doc_db_documents,
        assets_gtw_client=assets_gtw_client
    )


async def cdn_apps_server_config_py_youwol():
    env = await yw_config()
    return cdn_apps_server.Configuration(
        assets_gtw_client=LocalClients.get_assets_gateway_client(env=env)
    )
