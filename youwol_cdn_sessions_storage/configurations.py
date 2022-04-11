from dataclasses import dataclass
from typing import Dict, Callable, Optional, Awaitable

from youwol_utils import Storage


@dataclass(frozen=True)
class Constants:
    namespace: str = "cdn-sessions-storage"
    default_owner: str = "/youwol-users"


@dataclass(frozen=True)
class Configuration:

    storage: Storage
    admin_headers: Optional[Dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
