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
    """
    Abstract base class for defining the interface of a TokensStorage.

    A TokensStorage is responsible for persisting and retrieving token data associated
    with a unique tokens identifier and, optionally, a session identifier.
    """

    @abstractmethod
    async def get(self, tokens_id: str) -> Optional[TokensData]:
        """
        Retrieve token data based on the provided tokens identifier.

        Parameters:
            tokens_id: The unique identifier for the tokens.

        Return:
            The retrieved token data or None if not found.
        """

    @abstractmethod
    async def delete(self, tokens_id: str, session_id: str) -> None:
        """
        Delete token data associated with the provided tokens and session identifiers.

        Parameters:
            tokens_id: The unique identifier for the tokens.
            session_id: The session identifier associated with the tokens.

        Raises:
            TokensNotFoundError: Raised if the specified tokens are not found.
        """

    @abstractmethod
    async def get_by_sid(
        self, session_id: str
    ) -> tuple[Optional[str], Optional[TokensData]]:
        """
        Retrieve tokens identifier and associated token data based on the session identifier.

        Parameters:
            session_id (str): The session identifier.

        Return:
            A tuple containing the tokens identifier and associated token data or (None, None) if not found.
        """

    @abstractmethod
    async def store(self, tokens_id: str, data: TokensData) -> None:
        """
        Persist token data associated with the provided tokens identifier.

        Parameters:
            tokens_id: The unique identifier for the tokens.
            data: The token data to be stored.
        """


class Tokens:
    """
    Represents tokens used in the OIDC (OpenID Connect) protocol.

    This class manages various tokens, such as access tokens, ID tokens, and refresh tokens,
    associated with an OIDC client. It provides methods for accessing, refreshing, and managing
    the lifecycle of these tokens.
    """

    def __init__(
        self,
        tokens_id: str,
        storage: TokensStorage,
        oidc_client: OidcForClient,
        tokens_data: TokensData,
    ):
        """
        Initializes the instance with provided arguments.

        Parameters:
            tokens_id: A unique identifier for the tokens.
            storage: An instance of TokensStorage for persisting token data.
            oidc_client: An instance of OidcForClient for OIDC-related operations.
            tokens_data: An instance of TokensData containing token information.
        """
        self.__id = tokens_id
        self.__storage = storage
        self.__oidc_client = oidc_client
        self.__data = tokens_data

    def id(self) -> str:
        """
        Returns the unique identifier for the tokens.

        Return:
            The unique identifier for the tokens.
        """
        return self.__id

    async def username(self) -> str:
        """
        Returns the username associated with the ID token.

        Return:
            The username associated with the ID token.
        """
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__data.id_token)
        return str(decoded_id_token["upn"])

    async def sub(self) -> str:
        """
        Returns the subject identifier associated with the ID token.

        Return:
            The subject identifier associated with the ID token.
        """
        self.__assert_refresh_not_expired()
        decoded_id_token = await self.__oidc_client.token_decode(self.__data.id_token)
        return str(decoded_id_token["sub"])

    async def access_token(self) -> str:
        """
        Returns the access token, refreshing it if necessary.

        Return:
            The access token.
        """
        self.__assert_refresh_not_expired()

        if self.__data.expires_at < self.__now():
            await self.refresh()

        return self.__data.access_token

    def id_token(self) -> str:
        """
        Returns the ID token.

        Return:
            The ID token.
        """
        self.__assert_refresh_not_expired()
        return self.__data.id_token

    def __assert_refresh_not_expired(self) -> None:
        if self.__data.refresh_expires_at < self.__now():
            raise TokensExpiredError()

    async def delete(self) -> None:
        """
        Deletes the stored tokens associated with the current instance.

        Raises:
            TokensExpiredError: Raised if attempting to delete expired tokens.
        """
        await self.__storage.delete(
            tokens_id=self.id(), session_id=self.__data.session_state
        )

    async def save(self) -> None:
        """
        Persists the current tokens data.
        """
        await self.__storage.store(
            tokens_id=self.id(),
            data=self.__data,
        )

    def remaining_time(self) -> int:
        """
        Returns the remaining time (in seconds) until the next token refresh.

        Return:
            int: The remaining time until the next token refresh.
        """
        self.__assert_refresh_not_expired()
        return int(self.__data.refresh_expires_at - self.__now())

    async def refresh(self) -> None:
        """
        Refreshes the access and refresh tokens and updates the stored data.

        Raises:
            TokensExpiredError: Raised if attempting to refresh expired tokens.
        """
        self.__assert_refresh_not_expired()
        tokens_data = await self.__oidc_client.refresh(self.__data.refresh_token)
        self.__data = tokens_data
        await self.save()

    @staticmethod
    def __now() -> float:
        return datetime.datetime.now().timestamp()


class TokensManager:
    """
    Manager class for handling operations related to user tokens.
    """

    def __init__(self, storage: TokensStorage, oidc_client: OidcForClient):
        """
        Initializes a new instance of TokensManager.

        Parameters:
            storage: The storage mechanism for tokens.
            oidc_client: The OIDC client used for token operations.
        """
        self.__storage = storage
        self.__oidc_client = oidc_client

    async def save_tokens(self, tokens_id: str, tokens_data: TokensData) -> Tokens:
        """
        Saves tokens with the provided tokens_id and tokens_data.

        Parameters:
            tokens_id: The ID associated with the tokens.
            tokens_data: The data representing the tokens.

        Return:
             The created token.
        """
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
        """
        Restores tokens associated with the given tokens_id.

        Parameters:
            tokens_id: The ID associated with the tokens.

        Return:
            An instance of Tokens if found, otherwise None.
        """
        result = None

        tokens_data = await self.__storage.get(tokens_id)
        if tokens_data is None:
            return result

        tokens = Tokens(
            tokens_id=tokens_id,
            storage=self.__storage,
            oidc_client=self.__oidc_client,
            tokens_data=tokens_data,
        )

        try:
            await tokens.access_token()
            result = tokens
        except RuntimeError:
            await self.__storage.delete(
                tokens_id=tokens_id, session_id=tokens_data.session_state
            )
        return result

    async def restore_tokens_from_session_id(
        self,
        session_id: str,
    ) -> Optional[Tokens]:
        """
        Restores tokens associated with the given session_id.

        Parameters:
            session_id: The session ID associated with the tokens.

        Return:
            An instance of Tokens if found, otherwise None.
        """
        tokens_id, tokens_data = await self.__storage.get_by_sid(session_id)
        if tokens_id is None or tokens_data is None:
            return None
        return await self.restore_tokens(tokens_id)


class TokensStorageCache(TokensStorage):
    """
    Caching implementation of TokensStorage using a cache client.
    """

    _CACHE_SID_KEY_PREFIX = "sid"
    """
    Prefix for cache keys related to session IDs.
    """
    _CACHE_TOKENS_KEY_PREFIX = "tokens"
    """
    Prefix for cache keys related to tokens.
    """

    @staticmethod
    def cache_token_key(tokens_id: str) -> str:
        """
        Generates a cache key for tokens based on the provided tokens_id.

        Parameters:
            tokens_id: The ID associated with the tokens.

        Returns:
            The cache key for tokens.
        """
        return f"{TokensStorageCache._CACHE_TOKENS_KEY_PREFIX}_{tokens_id}"

    @staticmethod
    def cache_sid_key(session_id: str) -> str:
        """
        Generates a cache key for session IDs based on the provided session_id.

        Parameters:
            session_id: The session ID associated with the tokens.

        Returns:
            The cache key for session IDs.
        """
        return f"{TokensStorageCache._CACHE_SID_KEY_PREFIX}_{session_id}"

    async def get(self, tokens_id: str) -> Optional[TokensData]:
        """
        Retrieves tokens data from the cache based on the provided tokens_id.

        Parameters:
            tokens_id: The ID associated with the tokens.

        Return:
            An instance of TokensData if data is found in the cache, otherwise None.
        """
        cache_token_key = TokensStorageCache.cache_token_key(tokens_id)
        data = self.__cache.get(cache_token_key)
        if data is None:
            return None
        if not isinstance(data, dict):
            raise ValueError(f"Cached value for key {cache_token_key} is not a `dict`")
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
            self.__cache.delete(cache_token_key)
            return None

    async def delete(self, tokens_id: str, session_id: str) -> None:
        """
        Deletes tokens and session ID related entries from the cache.

        Parameters:
            tokens_id: The ID associated with the tokens.
            session_id: The session ID associated with the tokens.
        """
        self.__cache.delete(TokensStorageCache.cache_token_key(tokens_id))
        self.__cache.delete(TokensStorageCache.cache_sid_key(session_id))

    async def get_by_sid(
        self, session_id: str
    ) -> tuple[Optional[str], Optional[TokensData]]:
        """
        Retrieves tokens_id and tokens data from the cache based on the provided session_id.

        Parameters:
            session_id: The session ID associated with the tokens.

        Returns:
            A tuple containing tokens_id and TokensData if data is found in the cache, otherwise (None, None).
        """
        cache_sid_key = TokensStorageCache.cache_sid_key(session_id)
        tokens_id = self.__cache.get(cache_sid_key)
        if tokens_id is None:
            return None, None
        if not isinstance(tokens_id, str):
            raise ValueError(f"Cached value for key {cache_sid_key} is not a `str`")
        return tokens_id, await self.get(tokens_id)

    async def store(self, tokens_id: str, data: TokensData) -> None:
        """
        Stores tokens data in the cache.

        Parameters:
            tokens_id: The ID associated with the tokens.
            data: The data representing the tokens.
        """
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
        """
        Initializes a new instance with provided cache.

        Parameters:
            cache: The cache client used for storing and retrieving data.
        """
        self.__cache = cache


class SessionLessTokenManager:
    """
    Manages session-less access tokens using a cache.
    """

    __TOKEN_EXPIRES_AT_THRESHOLD: int = 15
    """
    Default threshold in seconds to consider an access token as expired.
    """

    def __init__(
        self,
        cache_key: str,
        cache: CacheClient,
        oidc_client: OidcForClient,
        expires_at_threshold=__TOKEN_EXPIRES_AT_THRESHOLD,
    ) -> None:
        """
        Initializes a new instance.

        Parameters:
            cache_key: The key used for storing and retrieving access token data from the cache.
            cache: The cache client used for storing and retrieving data.
            oidc_client: The OIDC client for obtaining access tokens.
            expires_at_threshold: Threshold value to consider an access token as expired.
        """

        self.__cache_key = cache_key
        self.__cache = cache
        self.__oidc_client = oidc_client
        self.__expires_at_threshold = expires_at_threshold

    async def get_access_token(self) -> str:
        """
        Retrieves a session-less access token from the cache or OIDC client.

        Returns
            The session-less access token.
        """

        now = datetime.datetime.now().timestamp()
        token_data = self.__cache.get(self.__cache_key)
        if not isinstance(token_data, dict):
            raise ValueError(f"Cached value for key {self.__cache_key} is not a `dict`")
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
