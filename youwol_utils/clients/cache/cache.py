import json
from dataclasses import dataclass
from typing import Optional, Union

from youwol_utils.types import JSON


class ttl(int):
    pass


class at(int):
    pass


@dataclass(frozen=False)
class CacheClient:
    prefix: str = ""

    def get(self, name: str) -> Optional[JSON]:
        val = self._impl_get(self._name_to_key(name))
        return json.loads(val) if val else None

    def set(self, name: str, content: JSON, expire: Union[ttl, at, None] = None):

        key = self._name_to_key(name)
        value = json.dumps(content)

        if expire is None:
            self._impl_set(key, value)
        elif isinstance(expire, at):
            self._impl_set_expire_at(key, value, unix_timestamp=expire)
        elif isinstance(expire, ttl):
            self._impl_set_expire_in(key, value, ttl=expire)

    def _impl_get(self, key: str) -> str:
        raise NotImplementedError()

    def _impl_set(self, key: str, value: str):
        raise NotImplementedError()

    def _impl_set_expire_in(self, key: str, value: str, ttl: int):
        raise NotImplementedError()

    def _impl_set_expire_at(self, key: str, value: str, unix_timestamp: int):
        raise NotImplementedError()

    def _name_to_key(self, name: str):
        return f"{self.prefix}_{name}"
