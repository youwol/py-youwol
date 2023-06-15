# standard library
import secrets

from dataclasses import dataclass

# typing
from typing import Any, ClassVar

# Youwol utilities
from youwol.utils import TTL, CacheClient


@dataclass(frozen=True)
class Flow:
    _CACHE_KEY_PREFIX: ClassVar[str] = "flow"
    _CACHE_TTL_FIVE_MINUTES: ClassVar[int] = 60 * 5

    ref: str
    cache: CacheClient

    @classmethod
    def cache_key(cls, uuid: str) -> str:
        return f"{cls._CACHE_KEY_PREFIX}_{uuid}"

    @staticmethod
    def random_ref() -> str:
        return secrets.token_urlsafe()

    def save(self) -> None:
        self.cache.set(
            self.cache_key(self.ref),
            {"ref": self.ref, **self._save()},
            TTL(self._CACHE_TTL_FIVE_MINUTES),
        )

    def _save(self) -> dict[str, Any]:
        return {}

    def delete(self) -> None:
        self.cache.delete(self.cache_key(self.ref))


@dataclass(frozen=True)
class AuthorizationFlow(Flow):
    _CACHE_KEY_PREFIX: ClassVar[str] = "auth_flow_state"

    target_uri: str
    code_verifier: str
    nonce: str

    def _save(self) -> dict[str, Any]:
        return {
            "target_uri": self.target_uri,
            "code_verifier": self.code_verifier,
            "nonce": self.nonce,
        }


@dataclass(frozen=True)
class LogoutFlow(Flow):
    _CACHE_KEY_PREFIX: ClassVar[str] = "logout_flow_state"

    target_uri: str
    forget_me: bool

    def _save(self) -> dict[str, Any]:
        return {"target_uri": self.target_uri, "forget_me": self.forget_me}
