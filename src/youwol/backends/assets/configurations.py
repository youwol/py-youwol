# standard library
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

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
    :attr:`namespace <youwol.backends.assets.configurations.Constants.namespace>`.
    """
    storage: Storage
    """
    DEPRECATED.
    The filesystem used to store media (images & thumbnails),
    it is planed to use `file_system` attributes client soon.
    """
    doc_db_asset: DocDb
    """
    NoSql client for this :glob:`table <youwol.utils.http_clients.assets_backend.models.ASSETS_TABLE>`
    included in this :attr:`namespace <youwol.backends.assets.configurations.Constants.namespace>`.
    """
    doc_db_access_history: DocDb
    doc_db_access_policy: DocDb
    """
    NoSql client for this :glob:`table <youwol.utils.http_clients.assets_backend.models.ACCESS_POLICY>`
    included in this :attr:`namespace <youwol.backends.assets.configurations.Constants.namespace>`.
    """
    admin_headers: dict[str, str] | None = None


class Dependencies:
    get_configuration: Callable[[], Configuration | Awaitable[Configuration]]


async def get_configuration() -> Configuration:
    """
    Returns:
        The configuration of the service.
    """
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
