# standard library
import datetime

# typing
from typing import Optional

# Youwol utilities
from youwol.utils import AT, CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient


class TokensExpiredError(RuntimeError):
    def __init__(self):
        super().__init__("Tokens expired")


class Tokens:
    EXPIRATION_THRESHOLD = 60
    _CACHE_SID_KEY_PREFIX = "sid"
    _CACHE_TOKENS_KEY_PREFIX = "tokens"

    def __init__(
        self,
        tokens_id: str,
        cache: CacheClient,
        oidc_client: OidcForClient,
        expires_at: Optional[float] = None,
        refresh_expires_at: Optional[float] = None,
        expiration_threshold: int = EXPIRATION_THRESHOLD,
        **tokens_data,
    ):
        self.__id = tokens_id
        self.__cache = cache
        self.__oidc_client = oidc_client
        self.__id_token = tokens_data["id_token"]
        self.__access_token = tokens_data["access_token"]
        self.__refresh_token = tokens_data["refresh_token"]
        self.__expires_at = (
            self.__ttl_to_at(tokens_data["expires_in"], expiration_threshold)
            if "expires_in" in tokens_data
            else expires_at
        )
        self.__refresh_expires_at = (
            self.__ttl_to_at(tokens_data["refresh_expires_in"], expiration_threshold)
            if "refresh_expires_in" in tokens_data
            else refresh_expires_at
        )

    def id(self):
        return self.__id

    async def username(self) -> str:
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__id_token)
        return decoded_id_token["upn"]

    async def sub(self) -> str:
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__id_token)
        return decoded_id_token["sub"]

    async def access_token(self):
        self.__assert_refresh_not_expired()

        if self.__expires_at < self.__now():
            await self.refresh()

        return self.__access_token

    def __assert_refresh_not_expired(self):
        if self.__refresh_expires_at < self.__now():
            raise TokensExpiredError()

    async def __sid(self) -> str:
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__id_token)
        return decoded_id_token["sid"]

    async def delete(self):
        session_id = await self.__sid()
        self.__cache.delete(Tokens.cache_token_key(self.id()))
        self.__cache.delete(Tokens.cache_sid_key(session_id))

    async def save(self):
        self.__cache.set(
            self.cache_token_key(self.id()),
            {
                "id_token": self.__id_token,
                "refresh_token": self.__refresh_token,
                "access_token": self.__access_token,
                "expires_at": self.__expires_at,
                "refresh_expires_at": self.__refresh_expires_at,
            },
            AT(self.__refresh_expires_at),
        )
        session_id = await self.__sid()
        self.__cache.set(Tokens.cache_sid_key(session_id), self.id())

    def remaining_time(self) -> int:
        self.__assert_refresh_not_expired()
        return int(self.__refresh_expires_at - self.__now())

    async def refresh(self, expiration_threshold: int = EXPIRATION_THRESHOLD):
        self.__assert_refresh_not_expired()
        tokens_data = await self.__oidc_client.refresh(self.__refresh_token)
        self.__id_token = tokens_data["id_token"]
        self.__refresh_token = tokens_data["refresh_token"]
        self.__access_token = tokens_data["access_token"]
        self.__expires_at = self.__ttl_to_at(
            tokens_data["expires_in"], expiration_threshold
        )
        self.__refresh_expires_at = self.__ttl_to_at(
            tokens_data["refresh_expires_in"], expiration_threshold
        )
        await self.save()

    @staticmethod
    def cache_token_key(tokens_id: str):
        return f"{Tokens._CACHE_TOKENS_KEY_PREFIX}_{tokens_id}"

    @staticmethod
    def cache_sid_key(session_id: str):
        return f"{Tokens._CACHE_SID_KEY_PREFIX}_{session_id}"

    @staticmethod
    def __now() -> float:
        return datetime.datetime.now().timestamp()

    @classmethod
    def __ttl_to_at(cls, ttl: int, expiration_threshold: int) -> float:
        return cls.__now() - expiration_threshold + ttl


async def save_tokens(
    tokens_id: str, cache: CacheClient, oidc_client: OidcForClient, **tokens_data
) -> Tokens:
    tokens = Tokens(
        tokens_id=tokens_id,
        cache=cache,
        oidc_client=oidc_client,
        **tokens_data,
    )
    await tokens.save()
    return tokens


def restore_tokens(
    tokens_id: str, cache: CacheClient, oidc_client: OidcForClient
) -> Optional[Tokens]:
    tokens_data = cache.get(Tokens.cache_token_key(tokens_id))
    if tokens_data is None:
        return None
    return Tokens(
        tokens_id=tokens_id, cache=cache, oidc_client=oidc_client, **tokens_data
    )


def restore_tokens_from_session_id(
    session_id: str, cache: CacheClient, oidc_client: OidcForClient
) -> Optional[Tokens]:
    tokens_id = cache.get(Tokens.cache_sid_key(session_id))
    if tokens_id is None:
        return None

    return restore_tokens(tokens_id=tokens_id, cache=cache, oidc_client=oidc_client)
