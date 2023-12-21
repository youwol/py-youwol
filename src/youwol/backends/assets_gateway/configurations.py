# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Callable, Union

# Youwol utilities
from youwol.utils import CdnClient
from youwol.utils.clients.assets.assets import AssetsClient
from youwol.utils.clients.files import FilesClient
from youwol.utils.clients.flux.flux import FluxClient
from youwol.utils.clients.stories.stories import StoriesClient
from youwol.utils.clients.treedb.treedb import TreeDbClient


@dataclass(frozen=True)
class Configuration:
    """
    Configuration of the service.
    """

    flux_client: FluxClient
    cdn_client: CdnClient
    """
    HTTP client to connect to the service `cdn`.
    """
    stories_client: StoriesClient
    treedb_client: TreeDbClient
    """
    HTTP client to connect to the 'files explorer' like service.
    """
    assets_client: AssetsClient
    """
    HTTP client to handle permissions.
    """
    files_client: FilesClient
    """
    HTTP client to retrieve assets of kind  ̀data`.
    """
    https: bool = False


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
