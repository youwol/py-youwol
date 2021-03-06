from dataclasses import dataclass
from typing import Dict, Callable, Union, Awaitable, Optional

from youwol_utils import (
    get_valid_bucket_name
)
from youwol_utils.http_clients.tree_db_backend import DocDbs


@dataclass(frozen=True)
class Constants:
    namespace: str = "tree-db"
    bucket: str = get_valid_bucket_name(namespace)
    default_owner = "/youwol-users"
    public_owner = '/youwol-users'
    text_content_type = "text/plain"


@dataclass(frozen=True)
class Configuration:
    doc_dbs: DocDbs
    admin_headers: Optional[Dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
