# standard library
from dataclasses import dataclass

# third parties
import redis

# relative
from .cache import TTL, CacheClient


@dataclass(frozen=False)
class RedisCacheClient(CacheClient):
    def __init__(self, host: str, prefix: str):
        super().__init__(prefix)
        self.cache = redis.Redis(host=host, decode_responses=True)

    def _impl_get(self, key: str) -> str | None:
        v = self.cache.get(key)
        return v if v is not None else None

    def _impl_set(self, key: str, value: str):
        self.cache.set(key, value)

    def _impl_set_expire_in(self, key: str, value: str, ttl: int):
        self.cache.set(key, value, ex=ttl)

    def _impl_set_expire_at(self, key: str, value: str, unix_timestamp: int):
        self.cache.set(key, value, exat=unix_timestamp)

    def _impl_delete(self, key: str):
        self.cache.delete(key)

    def _impl_get_ttl(self, key: str) -> TTL | None:
        exp = self.cache.ttl(key)
        if exp == "-1":
            return None
        if exp == "-2":
            raise Exception("Key not found")
        return TTL(exp)
