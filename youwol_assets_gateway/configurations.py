from dataclasses import dataclass
from typing import Callable, Union, Type, Awaitable, Dict, Optional

from youwol_utils import CdnClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.data_api.data import (
    DataClient, FILES_TABLE
)
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware
from youwol_assets_gateway.raw_stores.data import DataStore
from youwol_assets_gateway.raw_stores.flux_project import FluxProjectsStore
from youwol_assets_gateway.raw_stores.package import PackagesStore
from youwol_assets_gateway.raw_stores.story import StoriesStore

AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Constants:
    cache_prefix: str = "assets-gateway"
    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"

    table_data_schema = FILES_TABLE


@dataclass(frozen=True)
class Configuration:

    data_client: DataClient
    flux_client: FluxClient
    cdn_client: CdnClient
    stories_client: StoriesClient
    treedb_client: TreeDbClient
    assets_client: AssetsClient
    admin_headers: Optional[Dict[str, str]] = None

    def assets_stores(self):
        return [
            FluxProjectsStore(client=self.flux_client),
            PackagesStore(client=self.cdn_client),
            DataStore(client=self.data_client),
            StoriesStore(client=self.stories_client)
        ]


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
