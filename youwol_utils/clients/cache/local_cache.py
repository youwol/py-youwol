from typing import Union

from dataclasses import dataclass

from youwol_utils.types import JSON


@dataclass(frozen=True)
class LocalCacheClient:

    cache = {}

    prefix: str = ""

    async def set(self, name: str, value: any, ex: int,  **kwargs) -> bool:

        key = self._get_key(name)
        self.cache[key] = value
        return True

    async def get(self, name: str, **kwargs) -> Union[JSON, None]:

        key = self._get_key(name)
        if key not in self.cache:
            return None

        return self.cache[key]

    def _get_key(self, name: str):
        return self.prefix + name
