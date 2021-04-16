from typing import Any, Callable

from dataclasses import dataclass

from youwol.configuration.youwol_configuration import yw_config
from youwol_utils import get_valid_bucket_name
from .models import create_doc_dbs, DocDbs, namespace
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient
from fastapi.logger import logger


logger.info("Setup treedb-backend")


@dataclass(frozen=True)
class Configuration:

    open_api_prefix: str
    base_path: str

    doc_dbs: DocDbs

    admin_headers: Any

    cache_prefix: str = "treedb-backend"
    bucket: str = get_valid_bucket_name(namespace)

    namespace: str = namespace
    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"

    public_owner = '/youwol-users'


config_yw_treedb = None


async def get_configuration():

    global config_yw_treedb

    if config_yw_treedb:
        return config_yw_treedb

    config_yw = await yw_config()

    doc_dbs = create_doc_dbs(
        factory_db=LocalDocDbClient,
        root_path=config_yw.pathsBook.local_docdb
        )

    config_yw_treedb = Configuration(
        open_api_prefix='',
        base_path="/api/treedb-backend",
        doc_dbs=doc_dbs,
        admin_headers=None
        )

    return config_yw_treedb
