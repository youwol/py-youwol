import json
from dataclasses import dataclass
from typing import Union

from youwol_utils.types import JSON


@dataclass(frozen=False)
class CacheClient:

    host: str = ""
    prefix: str = ""

    def __post_init__(self):
        try:
            import redis
            self.cache = redis.Redis(host=self.host)
        except ModuleNotFoundError:
            pass

    async def get(self, name: str) -> Union[JSON, None]:
        val = self.cache.get(name=self._get_key(name))
        return json.loads(val) if val else None

    async def set(self, name: str, value: JSON, ex: int):
        return self.cache.set(name=self._get_key(name), value=json.dumps(value), ex=ex)

    def _get_key(self, name: str):
        return self.prefix + name
