from typing import Callable, Union, Type

from dataclasses import dataclass

from .models import STORIES_TABLE, DOCUMENTS_TABLE, DOCUMENTS_TABLE_BY_ID
from youwol.configuration.youwol_configuration import yw_config
from youwol_utils import (
    LocalDocDbClient, LocalStorageClient, DocDbClient, StorageClient, CacheClient, LocalCacheClient,
    )
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware

DocDb = Union[DocDbClient, LocalDocDbClient]
Storage = Union[StorageClient, LocalStorageClient]
Cache = Union[CacheClient, LocalCacheClient]
AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Configuration:

    open_api_prefix: str
    base_path: str
    storage: Storage
    doc_db_stories: DocDb
    doc_db_documents: DocDb

    namespace: str = "stories"

    cache_prefix: str = "stories-backend_"

    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"

    replication_factor: int = 2

    default_owner = "/youwol-users"

    local_http_port: int = 2534

    text_content_type = "text/plain"


config_yw_stories = None


async def get_configuration():

    global config_yw_stories

    if config_yw_stories:
        return config_yw_stories

    config_yw = await yw_config()
    storage = LocalStorageClient(
        root_path=config_yw.pathsBook.local_storage,
        bucket_name=Configuration.namespace
        )

    doc_db_stories = LocalDocDbClient(
        root_path=config_yw.pathsBook.local_docdb,
        keyspace_name=Configuration.namespace,
        table_body=STORIES_TABLE
        )

    doc_db_documents = LocalDocDbClient(
        root_path=config_yw.pathsBook.local_docdb,
        keyspace_name=Configuration.namespace,
        table_body=DOCUMENTS_TABLE,
        secondary_indexes=[DOCUMENTS_TABLE_BY_ID]
        )

    config_yw_stories = Configuration(
        open_api_prefix='',
        base_path="/api/stories-backend",
        storage=storage,
        doc_db_stories=doc_db_stories,
        doc_db_documents=doc_db_documents
        )
    return config_yw_stories
