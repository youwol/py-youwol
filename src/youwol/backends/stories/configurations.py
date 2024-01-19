# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Callable, Optional, Union

# Youwol utilities
from youwol.utils import (
    DocDbClient,
    LocalDocDbClient,
    LocalStorageClient,
    StorageClient,
)
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol.utils.http_clients.stories_backend import (
    DOCUMENTS_TABLE,
    DOCUMENTS_TABLE_BY_ID,
    STORIES_TABLE,
    Content,
    GlobalContent,
)

DocDb = Union[DocDbClient, LocalDocDbClient]
Storage = Union[StorageClient, LocalStorageClient]


@dataclass(frozen=True)
class Constants:
    namespace: str = "stories"
    cache_prefix: str = "stories-backend_"
    default_owner = "/youwol-users"
    text_content_type = "text/plain"
    db_schema_documents = DOCUMENTS_TABLE
    db_schema_stories = STORIES_TABLE
    db_schema_doc_by_id = DOCUMENTS_TABLE_BY_ID
    global_content_filename = "global-contents"
    global_default_content = GlobalContent(
        css="/*provides the list of rules that apply on all pages*/",
        javascript="return async (window) => {}",
        components="""
class BlockEx{
    label = "BlockEx"
    content = "<div> Hello blocks :) </div>"
    constructor({appState,grapesEditor,idFactory}){
        this.blockType = idFactory(this.label)
    }
}
return async () => ({
    getComponents: () => [],
    getBlocks: () => [BlockEx]
})
""",
    )

    @staticmethod
    def get_default_doc(document_id):
        return Content(
            html=f'<div id="{document_id}" '
            f'data-gjs-type="root" class="root" style="height:100%; width:100%; overflow:auto"></div>',
            css="",
            components="",
            styles="",
        )


@dataclass(frozen=True)
class Configuration:
    storage: Storage
    doc_db_stories: DocDb
    doc_db_documents: DocDb
    assets_gtw_client: AssetsGatewayClient
    admin_headers: Optional[dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
