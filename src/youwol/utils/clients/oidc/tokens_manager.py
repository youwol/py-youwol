# standard library
import datetime

# typing
from typing import Any, Optional

# Youwol utilities
from youwol.utils import AT, CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient, TokensData


class TokensExpiredError(RuntimeError):
    def __init__(self) -> None:
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
        **tokens_data: Any,
    ):
        self.__id = tokens_id
        self.__cache = cache
        self.__oidc_client = oidc_client
        self.__id_token = str(tokens_data["id_token"])
        self.__access_token = str(tokens_data["access_token"])
        self.__refresh_token = str(tokens_data["refresh_token"])
        self.__session_state = str(tokens_data["session_state"])

        if "expires_in" in tokens_data:
            self.__expires_at = self.__ttl_to_at(
                int(tokens_data["expires_in"]), expiration_threshold
            )
        elif expires_at is None:
            raise RuntimeError()
        else:
            self.__expires_at = expires_at

        if "refresh_expires_in" in tokens_data:
            self.__refresh_expires_at = self.__ttl_to_at(
                int(tokens_data["refresh_expires_in"]), expiration_threshold
            )
        elif refresh_expires_at is None:
            raise RuntimeError()
        else:
            self.__refresh_expires_at = refresh_expires_at

    def id(self) -> str:
        return self.__id

    async def username(self) -> str:
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__id_token)
        return str(decoded_id_token["upn"])

    async def sub(self) -> str:
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__id_token)
        return str(decoded_id_token["sub"])

    async def access_token(self) -> str:
        self.__assert_refresh_not_expired()

        if self.__expires_at < self.__now():
            await self.refresh()

        return self.__access_token

    def __assert_refresh_not_expired(self) -> None:
        if self.__refresh_expires_at < self.__now():
            raise TokensExpiredError()

    async def delete(self) -> None:
        self.__cache.delete(Tokens.cache_token_key(self.id()))
        self.__cache.delete(Tokens.cache_sid_key(self.__session_state))

    async def save(self) -> None:
        self.__cache.set(
            Tokens.cache_token_key(self.id()),
            {
                "id_token": self.__id_token,
                "refresh_token": self.__refresh_token,
                "access_token": self.__access_token,
                "expires_at": self.__expires_at,
                "refresh_expires_at": self.__refresh_expires_at,
                "session_state": self.__session_state,
            },
            AT(self.__refresh_expires_at),
        )
        self.__cache.set(
            Tokens.cache_sid_key(self.__session_state),
            self.id(),
            AT(self.__refresh_expires_at),
        )

    def remaining_time(self) -> int:
        self.__assert_refresh_not_expired()
        return int(self.__refresh_expires_at - self.__now())

    async def refresh(self, expiration_threshold: int = EXPIRATION_THRESHOLD) -> None:
        self.__assert_refresh_not_expired()
        tokens_data = await self.__oidc_client.refresh(self.__refresh_token)
        self.__id_token = tokens_data.id_token
        self.__refresh_token = tokens_data.refresh_token
        self.__access_token = tokens_data.access_token
        self.__expires_at = self.__ttl_to_at(
            tokens_data.expires_in, expiration_threshold
        )
        self.__refresh_expires_at = self.__ttl_to_at(
            tokens_data.refresh_expires_in, expiration_threshold
        )
        await self.save()

    @staticmethod
    def cache_token_key(tokens_id: str) -> str:
        return f"{Tokens._CACHE_TOKENS_KEY_PREFIX}_{tokens_id}"

    @staticmethod
    def cache_sid_key(session_id: str) -> str:
        return f"{Tokens._CACHE_SID_KEY_PREFIX}_{session_id}"

    @staticmethod
    def __now() -> float:
        return datetime.datetime.now().timestamp()

    @classmethod
    def __ttl_to_at(cls, ttl: int, expiration_threshold: int) -> float:
        return cls.__now() - expiration_threshold + ttl


class TokensManager:
    def __init__(self, cache: CacheClient, oidc_client: OidcForClient):
        self.__cache = cache
        self.__oidc_client = oidc_client

    async def save_tokens(self, tokens_id: str, tokens_data: TokensData) -> Tokens:
        tokens = Tokens(
            tokens_id=tokens_id,
            cache=self.__cache,
            oidc_client=self.__oidc_client,
            id_token=tokens_data.id_token,
            access_token=tokens_data.access_token,
            refresh_token=tokens_data.refresh_token,
            expires_in=tokens_data.expires_in,
            refresh_expires_in=tokens_data.refresh_expires_in,
            session_state=tokens_data.session_state,
        )
        await tokens.save()
        return tokens

    def restore_tokens(
        self,
        tokens_id: str,
    ) -> Optional[Tokens]:
        cache_token_key = Tokens.cache_token_key(tokens_id)
        tokens_data = self.__cache.get(cache_token_key)
        if tokens_data is None:
            return None
        try:
            return Tokens(
                tokens_id=tokens_id,
                cache=self.__cache,
                oidc_client=self.__oidc_client,
                **tokens_data,
            )
        except KeyError:
            self.__cache.delete(cache_token_key)
            return None

    def restore_tokens_from_session_id(
        self,
        session_id: str,
    ) -> Optional[Tokens]:
        tokens_id = self.__cache.get(Tokens.cache_sid_key(session_id))
        if tokens_id is None:
            return None

        return self.restore_tokens(tokens_id=tokens_id)


class SessionLessTokenManager:
    __TOKEN_EXPIRES_AT_THRESHOLD = 15

    def __init__(
        self,
        cache_key: str,
        cache: CacheClient,
        oidc_client: OidcForClient,
        expires_at_threshold=__TOKEN_EXPIRES_AT_THRESHOLD,
    ) -> None:
        self.__cache_key = cache_key
        self.__cache = cache
        self.__oidc_client = oidc_client
        self.__expires_at_threshold = expires_at_threshold

    async def get_access_token(self) -> str:
        now = datetime.datetime.now().timestamp()
        token_data = self.__cache.get(self.__cache_key)
        if token_data is None or int(token_data["expires_at"]) < int(now):
            sessionless_tokens_data = await self.__oidc_client.client_credentials_flow()
            expires_at = (
                int(now)
                + sessionless_tokens_data.expires_in
                - self.__expires_at_threshold
            )
            token_data = {
                "access_token": sessionless_tokens_data.access_token,
                "expires_at": expires_at,
            }
            self.__cache.set(
                self.__cache_key,
                token_data,
                AT(expires_at),
            )

        return str(token_data["access_token"])
