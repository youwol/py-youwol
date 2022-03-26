from dataclasses import dataclass
from typing import Union, Any, Coroutine, Dict, Optional

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol.web_socket import AdminContextLogger
from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.context import ContextLogger
from .models import LIBRARIES_TABLE


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolEnvironment
    # there are no required libs in local install: they will be fetched from remote anyway
    required_libs = []

    root_path: str
    base_path: str
    storage: any
    doc_db: Union[DocDb, LocalDocDb]

    admin_headers: Union[Coroutine[Any, Any, Dict[str, str]], None]

    namespace: str = "cdn"
    replication_factor: int = 2
    owner: str = "/youwol-users"

    allowed_prerelease = ['wip', 'alpha', 'alpha-wip', 'beta', 'beta-wip']
    ctx_logger: ContextLogger = AdminContextLogger()


config_yw_cdn: Optional[Configuration] = None


async def get_configuration(config_yw=None):
    global config_yw_cdn
    if not config_yw:
        config_yw = await yw_config()

    if config_yw_cdn and config_yw_cdn.yw_config == config_yw:
        return config_yw_cdn

    storage = LocalStorage(root_path=config_yw.pathsBook.local_storage,
                           bucket_name=Configuration.namespace)

    doc_db = LocalDocDb(root_path=config_yw.pathsBook.local_docdb,
                        keyspace_name=Configuration.namespace,
                        table_body=LIBRARIES_TABLE)

    config_yw_cdn = Configuration(
        yw_config=config_yw,
        root_path="",
        base_path="/api/cdn-backend",
        storage=storage,
        doc_db=doc_db,
        admin_headers=None
        )

    return config_yw_cdn
