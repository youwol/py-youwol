from dataclasses import dataclass
from typing import Callable, Union, Type, Optional

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol_utils import (
    LocalDocDbClient, LocalStorageClient, DocDbClient, StorageClient, CacheClient, LocalCacheClient,
)
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware
from .models import STORIES_TABLE, DOCUMENTS_TABLE, DOCUMENTS_TABLE_BY_ID

DocDb = Union[DocDbClient, LocalDocDbClient]
Storage = Union[StorageClient, LocalStorageClient]
Cache = Union[CacheClient, LocalCacheClient]
AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolEnvironment

    open_api_prefix: str
    base_path: str
    storage: Storage
    doc_db_stories: DocDb
    doc_db_documents: DocDb
    assets_gtw_client: AssetsGatewayClient

    namespace: str = "stories"

    cache_prefix: str = "stories-backend_"

    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"

    admin_headers = None
    replication_factor: int = 2

    default_owner = "/youwol-users"

    local_http_port: int = 2534

    text_content_type = "text/plain"


config_yw_stories: Optional[Configuration] = None


async def get_configuration(config_yw=None):

    global config_yw_stories
    if not config_yw:
        config_yw = await yw_config()

    if config_yw_stories and config_yw_stories.yw_config == config_yw:
        return config_yw_stories

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
    assets_gtw_client = AssetsGatewayClient(url_base=f"http://localhost:{config_yw.httpPort}/api/assets-gateway")

    config_yw_stories = Configuration(
        yw_config=config_yw,
        open_api_prefix='',
        base_path="/api/stories-backend",
        storage=storage,
        doc_db_stories=doc_db_stories,
        doc_db_documents=doc_db_documents,
        assets_gtw_client=assets_gtw_client
    )
    return config_yw_stories
