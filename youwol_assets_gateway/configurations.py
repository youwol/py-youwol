from dataclasses import dataclass
from typing import Callable, Union, Type, Awaitable, Dict, Optional

from youwol_utils import CdnClient
from youwol_utils.clients.assets.assets import AssetsClient

from youwol_utils.clients.files import FilesClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware

AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Constants:
    cache_prefix: str = "assets-gateway"
    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"


@dataclass(frozen=True)
class Configuration:

    flux_client: FluxClient
    cdn_client: CdnClient
    stories_client: StoriesClient
    treedb_client: TreeDbClient
    assets_client: AssetsClient
    files_client: FilesClient
    admin_headers: Optional[Dict[str, str]] = None
    deployed: bool = False


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
