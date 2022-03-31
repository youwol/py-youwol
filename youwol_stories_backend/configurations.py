
from dataclasses import dataclass
from typing import Union, Callable, Type, Awaitable

from youwol_utils import (
    CacheClient, LocalCacheClient, LocalDocDbClient,
    LocalStorageClient, DocDbClient, StorageClient
)
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.context import ContextLogger
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware
from youwol_utils.http_clients.stories_backend import DOCUMENTS_TABLE, STORIES_TABLE, DOCUMENTS_TABLE_BY_ID, Content

DocDb = Union[DocDbClient, LocalDocDbClient]
Storage = Union[StorageClient, LocalStorageClient]
Cache = Union[CacheClient, LocalCacheClient]
AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Constants:
    namespace: str = "stories"
    cache_prefix: str = "stories-backend_"
    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"
    default_owner = "/youwol-users"
    text_content_type = "text/plain"
    db_schema_documents = DOCUMENTS_TABLE
    db_schema_stories = STORIES_TABLE
    db_schema_doc_by_id = DOCUMENTS_TABLE_BY_ID
    default_doc = Content(
        html='<div data-gjs-type="root" class="root" style="height:100%; width:100%; overflow:auto"></div>',
        css='',
        components='',
        styles=''
    )


@dataclass(frozen=True)
class Configuration:

    storage: Storage
    doc_db_stories: DocDb
    doc_db_documents: DocDb
    assets_gtw_client: AssetsGatewayClient
    ctx_logger: ContextLogger
    admin_headers = None


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    return await Dependencies.get_configuration()
