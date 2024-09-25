# standard library
import json

from dataclasses import dataclass

# Youwol utilities
from youwol.utils.types import JSON


class TTL(int):
    """
    Expresses time to live deadline in seconds.
    """


class AT(int):
    """
    Expresses absolute time deadline in seconds since the Epoch.
    """


@dataclass(frozen=False)
class CacheClient:
    """
    Virtual class for cache implementation.
    """

    prefix: str = ""

    def get(self, name: str) -> JSON | None:
        """
        Parameters:
            name: Name of the entry.

        Returns:
            Corresponding value if the entry is found.
        """
        val = self._impl_get(self._name_to_key(name))
        return json.loads(val) if val else None

    def set(self, name: str, content: JSON, expire: TTL | AT | None = None) -> None:
        """
        Set an entry in the cache.

        Parameters:
            name: Entry's name.
            content: Entry's value.
            expire: Express validity duration, if any.
        """
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

    def get_ttl(self, name) -> TTL | None:
        key = self._name_to_key(name)
        return self._impl_get_ttl(key)

    def _impl_get(self, key: str) -> str | None:
        raise NotImplementedError()

    def _impl_set(self, key: str, value: str):
        raise NotImplementedError()

    def _impl_set_expire_in(self, key: str, value: str, ttl: int):
        raise NotImplementedError()

    def _impl_set_expire_at(self, key: str, value: str, unix_timestamp: int):
        raise NotImplementedError()

    def _impl_delete(self, key: str):
        raise NotImplementedError()

    def _impl_get_ttl(self, key: str) -> TTL | None:
        raise NotImplementedError()

    def _name_to_key(self, name: str):
        return f"{self.prefix}_{name}"
