from dataclasses import dataclass
from typing import Optional

import redis

from youwol_utils.clients.cache import CacheClient, TTL


@dataclass(frozen=False)
class RedisCacheClient(CacheClient):

    def __init__(self, host: str, prefix: str):
        super().__init__(prefix)
        self.cache = redis.Redis(host=host)

    def _impl_get(self, name: str) -> str:
        return self.cache.get(name)

    def _impl_set(self, name: str, value: str):
        self.cache.set(name, value)

    def _impl_set_expire_in(self, name: str, value: str, ttl: int):
        self.cache.set(name, value, ex=ttl)

    def _impl_set_expire_at(self, name: str, value: str, unix_timestamp: int):
        self.cache.set(name, value, exat=unix_timestamp)

    def _impl_delete(self, key: str):
        self.cache.delete(key)

    def _impl_get_ttl(self, key: str) -> Optional[TTL]:
        exp = self.cache.ttl(key)
        if exp == '-1':
            return None
        if exp == '-2':
            raise Exception("Key not found")
        return TTL(exp)
