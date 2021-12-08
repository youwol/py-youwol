from typing import Callable

from dataclasses import dataclass

from youwol.configuration.youwol_configuration import yw_config, YouwolConfiguration
from .models import ASSETS_TABLE, ACCESS_HISTORY, ACCESS_POLICY
from youwol_utils import Storage, DocDb, LocalStorageClient, LocalDocDbInMemoryClient
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient
from fastapi.logger import logger


logger.info("Setup assets-backend")


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolConfiguration

    open_api_prefix: str
    base_path: str
    storage: Storage
    doc_db_asset: DocDb
    doc_db_access_history: DocDb
    doc_db_access_policy: DocDb

    namespace: str = "assets"
    cache_prefix: str = "assets-backend"
    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"
    replication_factor: int = 2
    public_owner = '/youwol-users'
    doc_db_asset_version_table = "0.0"
    doc_db_access_history_version_table = "0.0"
    doc_db_access_policy_version_table = "0.0"


config_yw_assets = None


async def get_configuration(config_yw=None):
    global config_yw_assets
    if not config_yw:
        config_yw = await yw_config()

    if config_yw_assets and config_yw_assets.yw_config == config_yw:
        return config_yw_assets

    storage = LocalStorageClient(root_path=config_yw.pathsBook.local_storage,
                                 bucket_name=Configuration.namespace)

    doc_db_asset = LocalDocDbClient(root_path=config_yw.pathsBook.local_docdb,
                                    keyspace_name=Configuration.namespace,
                                    table_body=ASSETS_TABLE
                                    )

    doc_db_access_history = LocalDocDbInMemoryClient(root_path=config_yw.pathsBook.local_docdb,
                                                     keyspace_name=Configuration.namespace,
                                                     table_body=ACCESS_HISTORY
                                                     )

    doc_db_access_policy = LocalDocDbClient(root_path=config_yw.pathsBook.local_docdb,
                                            keyspace_name=Configuration.namespace,
                                            table_body=ACCESS_POLICY
                                            )
    config_yw_assets = Configuration(
        yw_config=config_yw,
        open_api_prefix='',
        base_path="/api/assets-backend",
        storage=storage,
        doc_db_asset=doc_db_asset,
        doc_db_access_history=doc_db_access_history,
        doc_db_access_policy=doc_db_access_policy
        )
    return config_yw_assets
