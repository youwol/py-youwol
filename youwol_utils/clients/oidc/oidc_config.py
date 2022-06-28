import urllib
import uuid
from enum import Enum
from typing import List, Union
from typing import Optional

import aiohttp
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel
from starlette.datastructures import URL


class ClientType(Enum):
    PUBLIC = 0
    PRIVATE = 1


class PrivateClient(BaseModel):
    type = ClientType.PRIVATE
    client_id: str
    client_secret: str


class PublicClient(BaseModel):
    type = ClientType.PUBLIC
    client_id: str


class OpenIdConfiguration(BaseModel):
    authorization_signing_alg_values_supported: List[str]
    authorization_endpoint: str
    token_endpoint: str
    end_session_endpoint: str
    jwks_uri: str


class OidcConfig:
    _base_url: str
    _openid_configuration: Optional[OpenIdConfiguration]
    _jwks_client: Optional[PyJWKClient]

    def __init__(self, base_url: str):
        self._base_url = base_url
        self._jwks_client = None
        self._openid_configuration = None

    def for_client(self, client: Union[PublicClient, PrivateClient]) -> "OidcForClient":
        return OidcForClient(self, client)

    async def token_decode(self, token: str):
        jwks_client = await self.jwks_client()
        token_data = jwt.decode(jwt=token,
                                key=jwks_client.get_signing_key_from_jwt(token).key,
                                algorithms=await self.jwt_algos(),
                                options={"verify_aud": False})
        return token_data

    async def jwt_algos(self):
        conf = await self.openid_configuration()
        return conf.authorization_signing_alg_values_supported

    async def jwks_client(self):
        if self._jwks_client is None:
            conf = await self.openid_configuration()
            self._jwks_client = PyJWKClient(conf.jwks_uri)
        return self._jwks_client

    async def openid_configuration(self):
        if self._openid_configuration is None:
            well_known_url = f"{self._base_url}/.well-known/openid-configuration"
            async with aiohttp.ClientSession() as session:
                async with session.get(well_known_url) as resp:
                    if resp.status != 200:
                        raise Exception(f"Cannot fetch OpenId configuration at well-known URL '{well_known_url}'")
                    else:
                        json = await resp.json()
            self._openid_configuration = OpenIdConfiguration.parse_obj(json)

        return self._openid_configuration


class OidcForClient:

    def __init__(self, config: OidcConfig, client: PrivateClient):
        self._config = config
        self._client = client

    async def auth_flow_url(self, state: str, redirect_uri: str, login_hint: Optional[str]):
        conf = await self._config.openid_configuration()
        url = URL(conf.authorization_endpoint)
        params = {
            'response_type': 'code',
            'client_id': self._client.client_id,
            'state': state,
            'scope': 'openid',
            'nonce': str(uuid.uuid4()),
            'redirect_uri': urllib.parse.quote(redirect_uri, safe=':/'),
            'response_mode': 'query'
        }

        if self._client.type == ClientType.PRIVATE:
            params['client_secret'] = self._client.client_secret

        if login_hint:
            params['login_hint'] = login_hint

        return url.replace_query_params(**params)

    async def auth_flow_handle_cb(self, code: str, redirect_uri: str):
        conf = await self._config.openid_configuration()
        params = {
            'code': code,
            'grant_type': 'authorization_code',
            'client_id': self._client.client_id,
            'redirect_uri': redirect_uri
        }

        if self._client.type == ClientType.PRIVATE:
            params['client_secret'] = self._client.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint,
                                    data=params
                                    ) as resp:
                status = resp.status
                token = await resp.json()
                if status != 200:
                    raise Exception(f"Failed to get token : {token}")

        return token

    async def client_credentials_flow(self):
        if self._client.type != ClientType.PRIVATE:
            raise Exception(f"Client {self._client.client_id} is public !")
        conf = await self._config.openid_configuration()
        params = {
            'grant_type': 'client_credentials',
            'client_id': self._client.client_id,
            'client_secret': self._client.client_secret
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint,
                                    data=params
                                    ) as resp:
                status = resp.status
                tokens = await resp.json()
                if status != 200:
                    raise Exception(f"Failed to get token : {tokens}")

        return tokens

    async def direct_flow(self, username: str, password: str):
        conf = await self._config.openid_configuration()

        params = {
            'grant_type': 'password',
            'username': username,
            'password': password,
            'client_id': self._client.client_id,
        }

        if self._client.type == ClientType.PRIVATE:
            params['client_secret'] = self._client.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint,
                                    data=params
                                    ) as resp:
                status = resp.status
                token = await resp.json()
                if status != 200:
                    raise Exception(f"Failed to get token : {token}")

        return token

    async def token_exchange(self, requested_subject: str, subject_token: str, check_role: Optional[str] =
    "impersonate"):

        conf = await self._config.openid_configuration()

        params = {
            'client_id': self._client.client_id,
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'subject_token': subject_token,
            'requested_token_type': 'urn:ietf:params:oauth:token-type:access_token',
            'requested_subject': requested_subject
        }

        if self._client.type == ClientType.PRIVATE:
            params['client_secret'] = self._client.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint,
                                    data=params
                                    ) as resp:
                status = resp.status
                token = await resp.json()
                if status != 200:
                    raise Exception(f"Failed to exchange token : {token}")

        return token

    async def logout_url(self, redirect_uri: str):
        conf = await self._config.openid_configuration()
        url = URL(conf.end_session_endpoint)
        return url.replace_query_params(redirect_uri=urllib.parse.quote(redirect_uri, safe=':/'))
