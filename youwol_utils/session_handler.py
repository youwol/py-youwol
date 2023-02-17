from typing import Any, Union

from youwol_utils import CacheClient, TTL
from youwol_utils.clients.oidc.oidc_config import OidcConfig, PrivateClient, PublicClient


class SessionHandler:
    __jwt_cache: CacheClient
    __session_uuid: str

    def __init__(self, jwt_cache: CacheClient, session_uuid: str):
        self.__jwt_cache = jwt_cache
        self.__session_uuid = session_uuid

    def store(self, tokens: Any):
        self.__jwt_cache.set(
            f"{self.__session_uuid}_access_token",
            {'v': tokens['access_token']},
            TTL(tokens['expires_in'])
        )
        self.__jwt_cache.set(
            f"{self.__session_uuid}_refresh_token",
            {'v': tokens['refresh_token']},
            TTL(tokens['refresh_expires_in'])
        )
        self.__jwt_cache.set(
            f"{self.__session_uuid}_id_token",
            {'v': tokens['id_token']},
            TTL(tokens['refresh_expires_in'])
        )

    def get_id_token(self):
        cached_item = self.__jwt_cache.get(f"{self.__session_uuid}_id_token")
        if cached_item:
            return cached_item['v']
        else:
            return None

    def get_uuid(self):
        return self.__session_uuid

    def get_remaining_time(self):
        return self.__jwt_cache.get_ttl(f"{self.__session_uuid}_refresh_token")

    def delete(self):
        self.__jwt_cache.delete(f"{self.__session_uuid}_access_token")
        self.__jwt_cache.delete(f"{self.__session_uuid}_refresh_token")
        self.__jwt_cache.delete(f"{self.__session_uuid}_id_token")

    def get_access_token(self):
        cached_item = self.__jwt_cache.get(f"{self.__session_uuid}_access_token")
        if cached_item:
            return cached_item['v']
        else:
            return None

    def get_refresh_token(self):
        cached_item = self.__jwt_cache.get(f"{self.__session_uuid}_refresh_token")
        if cached_item:
            return cached_item['v']
        else:
            return None

    async def refresh(self, openid_base_url: str, openid_client: Union[PublicClient, PrivateClient]) -> bool:
        refresh_token = self.__jwt_cache.get(f"{self.__session_uuid}_refresh_token")
        if refresh_token is None:
            return False

        tokens = await OidcConfig(base_url=openid_base_url).for_client(openid_client).refresh(
            refresh_token=refresh_token['v'])

        self.store(tokens)
        return True
