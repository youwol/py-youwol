# standard library
from dataclasses import dataclass

# typing
from typing import Any, ClassVar

# Youwol utilities
from youwol.utils import CacheClient


@dataclass(frozen=True)
class AbstractSharedState:
    _CACHE_KEY_PREFIX: ClassVar[str] = "state"

    uuid: str
    cache: CacheClient

    @classmethod
    def cache_key(cls, uuid: str):
        return f"{cls._CACHE_KEY_PREFIX}_{uuid}"

    def save(self):
        self.cache.set(self.cache_key(self.uuid), {"uuid": self.uuid, **self._save()})

    def _save(self) -> dict[str, Any]:
        return {}

    def delete(self):
        self.cache.delete(self.cache_key(self.uuid))


@dataclass(frozen=True)
class AuthorizationFlow(AbstractSharedState):
    _CACHE_KEY_PREFIX: ClassVar[str] = "auth_flow_state"

    target_uri: str
    code_verifier: str

    def _save(self) -> dict[str, Any]:
        return {"target_uri": self.target_uri, "code_verifier": self.code_verifier}


@dataclass(frozen=True)
class LogoutFlow(AbstractSharedState):
    _CACHE_KEY_PREFIX: ClassVar[str] = "logout_flow_state"

    target_uri: str
    forget_me: bool

    def _save(self) -> dict[str, Any]:
        return {"target_uri": self.target_uri, "forget_me": self.forget_me}
