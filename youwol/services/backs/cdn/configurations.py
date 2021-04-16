from typing import Union, Any, Coroutine, Dict

from dataclasses import dataclass

from youwol.configuration.youwol_configuration import yw_config
from .models import LIBRARIES_TABLE
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb


@dataclass(frozen=True)
class Configuration:

    required_libs = ["tslib#1.10.0", "rxjs#6.5.5", "lodash#4.17.15", "reflectmetadata#0.1.13", "bootstrap#4.4.1"]

    open_api_prefix: str
    base_path: str
    storage: any
    doc_db: Union[DocDb, LocalDocDb]

    admin_headers: Union[Coroutine[Any, Any, Dict[str, str]], None]

    namespace: str = "cdn"
    replication_factor: int = 2
    owner: str = "/youwol-users"


config_yw_cdn = None


async def get_configuration():

    global config_yw_cdn

    if config_yw_cdn:
        return config_yw_cdn

    config_yw = await yw_config()

    storage = LocalStorage(root_path=config_yw.pathsBook.local_storage,
                           bucket_name=Configuration.namespace)

    doc_db = LocalDocDb(root_path=config_yw.pathsBook.local_docdb,
                        keyspace_name=Configuration.namespace,
                        version_table="0.0",
                        table_body=LIBRARIES_TABLE)

    config_yw_cdn = Configuration(
        open_api_prefix='',
        base_path="/api/cdn-backend",
        storage=storage,
        doc_db=doc_db,
        admin_headers=None
        )

    return config_yw_cdn