# standard library
import datetime
import time

# typing
from typing import List, Optional

# third parties
import aiohttp

from pydantic import BaseModel
from starlette.datastructures import URL

# Youwol utilities
from youwol.utils import AT, CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient, SessionlessTokensData
from youwol.utils.clients.oidc.tokens_manager import (
    Tokens,
    TokensExpiredError,
    TokensManager,
)

TWELVE_HOURS = 12 * 60 * 60


class User(BaseModel):
    id: str
    username: str


class UsersManagement:
    async def get_temporary_users(self) -> List[User]:
        raise NotImplementedError()

    async def create_user(self, username: str, password: str) -> None:
        raise NotImplementedError()

    async def delete_user(self, username: str) -> None:
        raise NotImplementedError()


class KeycloakUsersManagement(UsersManagement):
    __SESSIONLESS_TOKEN_EXPIRES_AT_THRESHOLD = 15
    __KEYCLOAK_USERS_MANAGEMENT_TOKEN_CACHE_KEY = "keycloak_user_management_token"

    def __init__(self, realm_url: str, cache: CacheClient, oidc_client: OidcForClient):
        self.__realm_url = realm_url
        self.__oidc_client = oidc_client
        self.__cache = cache

    async def __get_access_token(self) -> str:
        now = datetime.datetime.now().timestamp()
        token_data = self.__cache.get(
            KeycloakUsersManagement.__KEYCLOAK_USERS_MANAGEMENT_TOKEN_CACHE_KEY
        )
        if token_data is None or token_data["expires_at"] < int(now):
            sessionless_tokens_data = await self.__oidc_client.client_credentials_flow()
            expires_at = (
                int(now)
                + sessionless_tokens_data.expires_in
                - KeycloakUsersManagement.__SESSIONLESS_TOKEN_EXPIRES_AT_THRESHOLD
            )
            token_data = {
                "access_token": sessionless_tokens_data.access_token,
                "expires_at": expires_at,
            }
            self.__cache.set(
                KeycloakUsersManagement.__KEYCLOAK_USERS_MANAGEMENT_TOKEN_CACHE_KEY,
                token_data,
                AT(expires_at),
            )

        return token_data["access_token"]

    async def get_temporary_users(self) -> List[User]:
        token = await self.__get_access_token()
        url = URL(f"{self.__realm_url}/users")
        params = {"briefRepresentation": "true", "q": "temporary_user:true"}
        url = url.replace_query_params(**params)
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.get(url=str(url)) as resp:
                content = await resp.json()
                if resp.status != 200:
                    raise Exception(f"Failed to list temporary users : {content}")

        return [User.parse_obj(item) for item in content]

    async def create_user(self, username: str, password: str) -> None:
        token = await self.__get_access_token()
        user = {
            "username": username,
            "email": username,
            "emailVerified": True,
            "enabled": True,
            "attributes": {"temporary_user": True},
            "groups": ["youwol-users"],
            "credentials": [
                {"temporary": False, "type": "password", "value": password}
            ],
        }
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.post(f"{self.__realm_url}/users", json=user) as resp:
                status = resp.status
                message = await resp.content.read()
                if status != 201:
                    raise Exception(
                        f"Failed to create user : {message.decode(encoding='UTF8')}"
                    )

    async def delete_user(self, user_id: str) -> None:
        token = await self.__get_access_token()
        url = URL(f"{self.__realm_url}/users/{user_id}")
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.delete(url=str(url)) as resp:
                if resp.status != 204:
                    content = await resp.content.read()
                    raise Exception(
                        f"Failed to delete user {user_id} : {content.decode(encoding='UTF8')}"
                    )

    async def register_user(
        self, sub: str, email: str, target_uri: str, client_id: str
    ) -> None:
        token = await self.__get_access_token()
        user = {
            "username": email,
            "email": email,
            "emailVerified": False,
            "enabled": True,
            "attributes": {
                "temporary_user": True,
                "registration_pending": int(time.time()) + TWELVE_HOURS,
            },
            "groups": ["youwol-users"],
        }

        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.put(
                f"{self.__realm_url}/users/{sub}", json=user
            ) as resp:
                status = resp.status
                if status != 204:
                    message = await resp.json()
                    raise Exception(
                        f"Failed to register user : {message['errorMessage']}"
                    )

        actions = ["UPDATE_PROFILE", "UPDATE_PASSWORD"]

        url = URL(f"{self.__realm_url}/users/{sub}/execute-actions-email")
        params = {
            "client_id": client_id,
            "redirect_uri": target_uri,
            "lifespan": TWELVE_HOURS,
        }
        url = url.replace_query_params(**params)
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.put(str(url), json=actions) as resp:
                status = resp.status
                if status != 204:
                    message = await resp.json()
                    raise Exception(f"Failed to setup actions : {message}")

    async def finalize_user(self, sub: str) -> None:
        token = await self.__get_access_token()
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.put(
                f"{self.__realm_url}/users/{sub}",
                json={
                    "attributes": {},
                },
            ) as resp:
                status = resp.status
                if status != 204:
                    message = await resp.json()
                    raise Exception(f"Failed to finalize user : {message}")
