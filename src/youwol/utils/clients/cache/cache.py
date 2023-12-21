# standard library
import json

from dataclasses import dataclass

# typing
from typing import Optional, Union

# Youwol utilities
from youwol.utils.types import JSON


class TTL(int):
    pass


class AT(int):
    pass


@dataclass(frozen=False)
class CacheClient:
    prefix: str = ""

    def get(self, name: str) -> Optional[JSON]:
        val = self._impl_get(self._name_to_key(name))
        return json.loads(val) if val else None

    def set(
        self, name: str, content: JSON, expire: Union[TTL, AT, None] = None
    ) -> None:
        key = self._name_to_key(name)
        value = json.dumps(content)

        if expire is None:
            self._impl_set(key, value)
        elif isinstance(expire, AT):
            self._impl_set_expire_at(key, value, unix_timestamp=expire)
        elif isinstance(expire, TTL):
            self._impl_set_expire_in(key, value, ttl=expire)

    def delete(self, name: str) -> None:
        key = self._name_to_key(name)
        self._impl_delete(key)

    def get_ttl(self, name) -> Optional[TTL]:
        key = self._name_to_key(name)
        return self._impl_get_ttl(key)

    def _impl_get(self, key: str) -> Optional[str]:
        raise NotImplementedError()

    def _impl_set(self, key: str, value: str):
        raise NotImplementedError()

    def _impl_set_expire_in(self, key: str, value: str, ttl: int):
        raise NotImplementedError()

    def _impl_set_expire_at(self, key: str, value: str, unix_timestamp: int):
        raise NotImplementedError()

    def _impl_delete(self, key: str):
        raise NotImplementedError()

    def _impl_get_ttl(self, key: str) -> Optional[TTL]:
        raise NotImplementedError()

    def _name_to_key(self, name: str):
        return f"{self.prefix}_{name}"
