# standard library
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Callable, Optional, Union

# Youwol utilities
from youwol.utils import FileSystemInterface, Storage
from youwol.utils.clients.types import DocDb


@dataclass(frozen=True)
class Constants:
    """
    Configuration's constants for the service.
    """

    namespace: str = "assets"
    """
    namespace of the service
    """
    public_owner = "/youwol-users"


@dataclass(frozen=True)
class Configuration:
    """
    Configuration of the service.
    """

    file_system: FileSystemInterface
    """
    File system client using a bucket defined by this
    [namespace](@yw-nav-attr:youwol.backends.assets.configurations.Constants.namespace).
    """
    storage: Storage
    """
    DEPRECATED.
    The filesystem used to store media (images & thumbnails),
    it is planed to use `file_system` attributes client soon.
    """
    doc_db_asset: DocDb
    """
    NoSql client for this [table](@yw-nav-glob:youwol.utils.http_clients.assets_backend.models.ASSETS_TABLE)
    included in this [namespace](@yw-nav-attr:youwol.backends.assets.configurations.Constants.namespace).
    """
    doc_db_access_history: DocDb
    doc_db_access_policy: DocDb
    """
    NoSql client for this [table](@yw-nav-glob:youwol.utils.http_clients.assets_backend.models.ACCESS_POLICY)
    included in this [namespace](@yw-nav-attr:youwol.backends.assets.configurations.Constants.namespace).
    """
    admin_headers: Optional[dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
