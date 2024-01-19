# standard library
import sys
import time

from threading import Event, Thread

# typing
from typing import Optional

# third parties
from pydantic import BaseModel

# relative
from .cache import TTL, CacheClient


class CacheEntry(BaseModel):
    value: str
    expire_at: int = sys.maxsize


class LocalCacheClient(CacheClient):
    _cache: dict[str, CacheEntry]

    def __init__(self, prefix: str):
        super().__init__(prefix=prefix)
        self._cache = {}

    def _impl_get(self, key: str) -> Optional[str]:
        return (
            self._cache[key].value
            if key in self._cache and self._cache[key].expire_at > int(time.time())
            else None
        )

    def _impl_set(self, key: str, value: str):
        self._cache[key] = CacheEntry(value=value)

    def _impl_set_expire_in(self, key: str, value: str, ttl: int):
        self._cache[key] = CacheEntry(value=value, expire_at=int(time.time()) + ttl)

    def _impl_set_expire_at(self, key: str, value: str, unix_timestamp: int):
        self._cache[key] = CacheEntry(value=value, expire_at=unix_timestamp)

    def _impl_delete(self, key: str):
        self._cache.pop(key, None)

    def _impl_get_ttl(self, key: str) -> Optional[TTL]:
        expire_at = self._cache[key].expire_at
        if expire_at == sys.maxsize:
            return None
        return TTL(int(expire_at - int(time.time())))

    def clear_expired(self):
        for key in [
            key
            for key, entry in self._cache.items()
            if entry.expire_at < int(time.time())
        ]:
            self._cache.pop(key, None)


class CleanerThread(Thread):
    __caches: list[LocalCacheClient]
    __stopping: Event
    __period: int

    def __init__(self, period: int = 5 * 60):
        super().__init__()
        self.__caches = []
        self.__period = period
        self.__stopping = Event()

    def add_cache(self, cache: LocalCacheClient):
        self.__caches.append(cache)

    def go(self):
        self.start()

    def join(self, timeout=0):
        if self.is_alive():
            self.__stopping.set()
            super().join()

    def run(self) -> None:
        while not self.__stopping.is_set():
            for cache in self.__caches:
                cache.clear_expired()
            self.__stopping.wait(timeout=self.__period)


def factory_local_cache(cleaner_thread: CleanerThread, prefix: str) -> CacheClient:
    result = LocalCacheClient(prefix)
    cleaner_thread.add_cache(result)
    return result
