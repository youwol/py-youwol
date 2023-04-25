# standard library
from dataclasses import dataclass

# typing
from typing import Awaitable, Callable, Dict, Optional, Union

# Youwol utilities
from youwol.utils import get_valid_bucket_name
from youwol.utils.http_clients.tree_db_backend import DocDbs


@dataclass(frozen=True)
class Constants:
    namespace: str = "tree-db"
    bucket: str = get_valid_bucket_name(namespace)
    default_owner = "/youwol-users"
    public_owner = "/youwol-users"
    text_content_type = "text/plain"
    # This is the limit of children that can be fetched for a folder/drive.
    # It has to disappear, see issue #158 files explorer: no max children count
    max_children_count = 1000


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
