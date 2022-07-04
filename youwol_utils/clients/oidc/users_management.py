from typing import Optional

import aiohttp
from pydantic import BaseModel
from starlette.datastructures import URL

from youwol_utils.clients.oidc.oidc_config import OidcForClient


class User(BaseModel):
    id: str
    username: str


class UsersManagement:

    def get_temporary_users(self):
        raise NotImplementedError()

    def create_user(self, username: str, password: str):
        raise NotImplementedError()

    def delete_user(self, username: str):
        raise NotImplementedError()


class KeycloakUsersManagement(UsersManagement):
    _realm_url: str
    _client: OidcForClient
    _token: Optional[str]

    def __init__(self, realm_url: str, client: OidcForClient):
        self._realm_url = realm_url
        self._client = client

    async def get_temporary_users(self):
        tokens = await self._client.client_credentials_flow()
        self._token = tokens['access_token']
        url = URL(f"{self._realm_url}/users")
        params = {
            "briefRepresentation": "true",
            "q": 'temporary_user:true'
        }
        url = url.replace_query_params(**params)
        async with aiohttp.ClientSession(headers={'Authorization': f"Bearer {self._token}"}) as session:
            async with session.get(url=str(url)) as resp:
                content = await resp.json()
                if resp.status != 200:
                    raise Exception(f"Failed to list temporary users : {content}")

        return [User.parse_obj(item) for item in content]

    async def create_user(self, username: str, password: str):
        tokens = await self._client.client_credentials_flow()
        self._token = tokens['access_token']

        user = {
            'email': username,
            'emailVerified': True,
            'enabled': True,
            'attributes': {
                'temporary_user': True
            },
            'groups': ['youwol-users'],
            'credentials': [{
                'temporary': False,
                'type': 'password',
                'value': password
            }],

        }
        async with aiohttp.ClientSession(headers={'Authorization': f"Bearer {self._token}"}) as session:
            async with session.post(f"{self._realm_url}/users", json=user) as resp:
                status = resp.status
                message = await resp.content.read()
                if status != 201:
                    raise Exception(f"Failed to create user : {message}")

    async def delete_user(self, user_id: str):
        tokens = await self._client.client_credentials_flow()
        self._token = tokens['access_token']
        url = URL(f"{self._realm_url}/users/{user_id}")
        async with aiohttp.ClientSession(headers={'Authorization': f"Bearer {self._token}"}) as session:
            async with session.delete(url=str(url)) as resp:
                if resp.status != 204:
                    content = await resp.read()
                    raise Exception(f"Failed to delete user {user_id} : {content}")
