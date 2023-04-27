# standard library
from dataclasses import dataclass

# typing
from typing import Awaitable, Callable, Dict, Optional, Type, Union

# Youwol utilities
from youwol.utils import CdnClient
from youwol.utils.clients.assets.assets import AssetsClient
from youwol.utils.clients.files import FilesClient
from youwol.utils.clients.flux.flux import FluxClient
from youwol.utils.clients.stories.stories import StoriesClient
from youwol.utils.clients.treedb.treedb import TreeDbClient
from youwol.utils.middlewares import Middleware
from youwol.utils.middlewares.authentication_local import AuthLocalMiddleware

AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Constants:
    cache_prefix: str = "assets-gateway"
    unprotected_paths: Callable[[str], bool] = (
        lambda url: url.path.split("/")[-1] == "healthz"
        or url.path.split("/")[-1] == "openapi-docs"
    )


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