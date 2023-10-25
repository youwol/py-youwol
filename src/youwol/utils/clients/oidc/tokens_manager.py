# standard library
import datetime

from abc import ABC, abstractmethod

# typing
from typing import Optional

# Youwol utilities
from youwol.utils import AT, CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient, TokensData


class TokensExpiredError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Tokens expired")


class TokensStorage(ABC):
    @abstractmethod
    async def get(self, tokens_id: str) -> Optional[TokensData]:
        pass

    @abstractmethod
    async def delete(self, tokens_id: str, session_id: str) -> None:
        pass

    @abstractmethod
    async def get_by_sid(
        self, session_id: str
    ) -> (Optional[str], Optional[TokensData]):
        pass

    @abstractmethod
    async def store(self, tokens_id: str, data: TokensData) -> None:
        pass


class Tokens:
    def __init__(
        self,
        tokens_id: str,
        storage: TokensStorage,
        oidc_client: OidcForClient,
        tokens_data: TokensData,
    ):
        self.__id = tokens_id
        self.__storage = storage
        self.__oidc_client = oidc_client
        self.__data = tokens_data

    def id(self) -> str:
        return self.__id

    async def username(self) -> str:
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__data.id_token)
        return str(decoded_id_token["upn"])

    async def sub(self) -> str:
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__data.id_token)
        return str(decoded_id_token["sub"])

    async def access_token(self) -> str:
        self.__assert_refresh_not_expired()

        if self.__data.expires_at < self.__now():
            await self.refresh()

        return self.__data.access_token

    def id_token(self) -> str:
        self.__assert_refresh_not_expired()
        return self.__data.id_token

    def __assert_refresh_not_expired(self) -> None:
        if self.__data.refresh_expires_at < self.__now():
            raise TokensExpiredError()

    async def delete(self) -> None:
        await self.__storage.delete(
            tokens_id=self.id(), session_id=self.__data.session_state
        )

    async def save(self) -> None:
        await self.__storage.store(
            tokens_id=self.id(),
            data=self.__data,
        )

    def remaining_time(self) -> int:
        self.__assert_refresh_not_expired()
        return int(self.__data.refresh_expires_at - self.__now())

    async def refresh(self) -> None:
        self.__assert_refresh_not_expired()
        tokens_data = await self.__oidc_client.refresh(self.__data.refresh_token)
        self.__data = tokens_data
        await self.save()

    @staticmethod
    def __now() -> float:
        return datetime.datetime.now().timestamp()


class TokensManager:
    def __init__(self, storage: TokensStorage, oidc_client: OidcForClient):
        self.__storage = storage
        self.__oidc_client = oidc_client

    async def save_tokens(self, tokens_id: str, tokens_data: TokensData) -> Tokens:
        tokens = Tokens(
            tokens_id=tokens_id,
            storage=self.__storage,
            oidc_client=self.__oidc_client,
            tokens_data=tokens_data,
        )
        await tokens.save()
        return tokens

    async def restore_tokens(
        self,
        tokens_id: str,
    ) -> Optional[Tokens]:
        tokens_data = await self.__storage.get(tokens_id)
        if tokens_data is None:
            return None
        result = Tokens(
            tokens_id=tokens_id,
            storage=self.__storage,
            oidc_client=self.__oidc_client,
            tokens_data=tokens_data,
        )
        try:
            await result.access_token()
        except RuntimeError:
            await self.__storage.delete(
                tokens_id=tokens_id, session_id=tokens_data.session_state
            )
            result = None
        return result

    async def restore_tokens_from_session_id(
        self,
        session_id: str,
    ) -> Optional[Tokens]:
        tokens_id, tokens_data = await self.__storage.get_by_sid(session_id)
        if tokens_id is None or tokens_data is None:
            return None
        return await self.restore_tokens(tokens_id)


class TokensStorageCache(TokensStorage):
    _CACHE_SID_KEY_PREFIX = "sid"
    _CACHE_TOKENS_KEY_PREFIX = "tokens"

    @staticmethod
    def cache_token_key(tokens_id: str) -> str:
        return f"{TokensStorageCache._CACHE_TOKENS_KEY_PREFIX}_{tokens_id}"

    @staticmethod
    def cache_sid_key(session_id: str) -> str:
        return f"{TokensStorageCache._CACHE_SID_KEY_PREFIX}_{session_id}"

    async def get(self, tokens_id: str) -> Optional[TokensData]:
        data = self.__cache.get(TokensStorageCache.cache_token_key(tokens_id))
        if data is None:
            return None
        try:
            return TokensData(
                id_token=str(data["id_token"]),
                access_token=str(data["access_token"]),
                refresh_token=str(data["refresh_token"]),
                session_state=str(data["session_state"]),
                expires_at=float(data["expires_at"]),
                refresh_expires_at=float(data["refresh_expires_at"]),
            )
        except KeyError:
            self.__cache.delete(TokensStorageCache.cache_token_key(tokens_id))
            return None

    async def delete(self, tokens_id: str, session_id: str) -> None:
        self.__cache.delete(TokensStorageCache.cache_token_key(tokens_id))
        self.__cache.delete(TokensStorageCache.cache_sid_key(session_id))

    async def get_by_sid(
        self, session_id: str
    ) -> (Optional[str], Optional[TokensData]):
        tokens_id: str = self.__cache.get(TokensStorageCache.cache_sid_key(session_id))
        if tokens_id is None:
            return None, None
        return tokens_id, await self.get(tokens_id)

    async def store(self, tokens_id: str, data: TokensData) -> None:
        self.__cache.set(
            TokensStorageCache.cache_token_key(tokens_id),
            {
                "id_token": data.id_token,
                "refresh_token": data.refresh_token,
                "access_token": data.access_token,
                "expires_at": data.expires_at,
                "refresh_expires_at": data.refresh_expires_at,
                "session_state": data.session_state,
            },
            AT(data.refresh_expires_at),
        )
        self.__cache.set(
            TokensStorageCache.cache_sid_key(data.session_state),
            tokens_id,
            AT(data.refresh_expires_at),
        )

    def __init__(self, cache: CacheClient):
        self.__cache = cache


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
