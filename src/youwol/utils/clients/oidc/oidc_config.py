# standard library
import base64
import hashlib
import random
import string
import uuid

from dataclasses import dataclass

# typing
from typing import Any, Dict, List, Optional, Tuple, Union

# third parties
import aiohttp
import jwt

from jwt import PyJWKClient
from pydantic import BaseModel
from starlette.datastructures import URL


class PrivateClient(BaseModel):
    client_id: str
    client_secret: str


class PublicClient(BaseModel):
    client_id: str


class OpenIdConfiguration(BaseModel):
    token_endpoint_auth_signing_alg_values_supported: List[str]
    authorization_endpoint: str
    token_endpoint: str
    end_session_endpoint: str
    jwks_uri: str


class InvalidTokensData(RuntimeError):
    def __init__(self, msg: str) -> None:
        super().__init__(f"Invalid tokens data: {msg}")


@dataclass(frozen=True)
class TokensData:
    id_token: str
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    session_state: str


def tokens_data(data: Any) -> TokensData:
    if "token_type" not in data:
        raise InvalidTokensData("no 'token_type' attribute")

    if "id_token" not in data:
        raise InvalidTokensData("No 'id_token' attribute")
    if "access_token" not in data:
        raise InvalidTokensData("No 'access_token' attribute")
    if "refresh_token" not in data:
        raise InvalidTokensData("No 'refresh_token' attribute")
    if "expires_in" not in data:
        raise InvalidTokensData("No 'expires_in' attribute")
    if "refresh_expires_in" not in data:
        raise InvalidTokensData("No 'refresh_expires_in' attribute")
    if "session_state" not in data:
        raise InvalidTokensData("No 'session_state' attribute")

    token_type = data["token_type"]
    if token_type != "Bearer":
        raise InvalidTokensData(f"not a Bearer token ('type': '{token_type}'))")

    return TokensData(
        id_token=str(data["id_token"]),
        access_token=str(data["access_token"]),
        refresh_token=str(data["refresh_token"]),
        expires_in=int(data["expires_in"]),
        refresh_expires_in=int(data["refresh_expires_in"]),
        session_state=str(data["session_state"]),
    )


@dataclass(frozen=True)
class SessionlessTokensData:
    access_token: str
    expires_in: int


def sessionless_tokens_data(data: Any) -> SessionlessTokensData:
    if "token_type" not in data:
        raise InvalidTokensData("no 'token_type' attribute")

    if "access_token" not in data:
        raise InvalidTokensData("No 'access_token' attribute")
    if "expires_in" not in data:
        raise InvalidTokensData("No 'expires_in' attribute")

    token_type = data["token_type"]
    if token_type != "Bearer":
        raise InvalidTokensData(f"not a Bearer token ('type': '{token_type}'))")

    return SessionlessTokensData(
        access_token=str(data["access_token"]),
        expires_in=int(data["expires_in"]),
    )


Client = Union[PrivateClient, PublicClient]


class OidcInfos(BaseModel):
    base_uri: str
    client: Client


class OidcConfig:
    base_url: str
    _openid_configuration: Optional[OpenIdConfiguration]
    _jwks_client: Optional[PyJWKClient]

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._jwks_client = None
        self._openid_configuration = None

    def for_client(self, client: Client) -> "OidcForClient":
        return OidcForClient(self, client)

    async def token_decode(self, token: str) -> Dict[str, Any]:
        jwks_client = await self.jwks_client()
        token_data = jwt.decode(
            jwt=token,
            key=jwks_client.get_signing_key_from_jwt(token).key,
            algorithms=await self.jwt_algos(),
            options={"verify_aud": False},
        )
        return token_data

    async def jwt_algos(self) -> List[str]:
        conf = await self.openid_configuration()
        return conf.token_endpoint_auth_signing_alg_values_supported

    async def jwks_client(self) -> PyJWKClient:
        if self._jwks_client is None:
            conf = await self.openid_configuration()
            self._jwks_client = PyJWKClient(conf.jwks_uri)
        return self._jwks_client

    async def openid_configuration(self) -> OpenIdConfiguration:
        if self._openid_configuration is None:
            well_known_url = f"{self.base_url}/.well-known/openid-configuration"
            async with aiohttp.ClientSession() as session:
                async with session.get(well_known_url) as resp:
                    if resp.status != 200:
                        raise RuntimeError(
                            f"Cannot fetch OpenId configuration at well-known URL '{well_known_url}'"
                        )
                    else:
                        json = await resp.json()
            self._openid_configuration = OpenIdConfiguration.parse_obj(json)

        return self._openid_configuration


def random_code_verifier() -> str:
    choices = string.ascii_letters + string.digits + "-._~"
    return "".join((random.choice(choices) for _ in range(128)))


class OidcForClient:
    def __init__(self, config: OidcConfig, client: Client):
        self._config = config
        self._client = client

    async def auth_flow_url(
        self, state: str, redirect_uri: str, login_hint: Optional[str]
    ) -> Tuple[str, str]:
        conf = await self._config.openid_configuration()
        url = URL(conf.authorization_endpoint)
        params = {
            "response_type": "code",
            "client_id": self._client.client_id,
            "state": state,
            "scope": "openid",
            "nonce": str(uuid.uuid4()),
            "redirect_uri": redirect_uri,
            "response_mode": "query",
        }

        if isinstance(self._client, PrivateClient):
            params["client_secret"] = self._client.client_secret

        if login_hint:
            params["login_hint"] = login_hint

        code_verifier = random_code_verifier()
        code_challenge = hashlib.sha256(code_verifier.encode("ascii")).digest()
        params["code_challenge"] = (
            base64.urlsafe_b64encode(code_challenge).decode("ascii").replace("=", "")
        )
        params["code_challenge_method"] = "S256"

        return str(url.replace_query_params(**params)), code_verifier

    async def auth_flow_handle_cb(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> TokensData:
        conf = await self._config.openid_configuration()
        params = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self._client.client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }

        if isinstance(self._client, PrivateClient):
            params["client_secret"] = self._client.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint, data=params) as resp:
                status = resp.status
                token = await resp.json()
                if status != 200:
                    raise RuntimeError(f"Failed to get token : {token}")

        return tokens_data(token)

    async def client_credentials_flow(self) -> SessionlessTokensData:
        if isinstance(self._client, PublicClient):
            raise RuntimeError(f"Client {self._client.client_id} is public !")
        conf = await self._config.openid_configuration()
        params = {
            "grant_type": "client_credentials",
            "client_id": self._client.client_id,
            "client_secret": self._client.client_secret,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint, data=params) as resp:
                status = resp.status
                tokens = await resp.json()
                if status != 200:
                    raise RuntimeError(f"Failed to get token : {tokens}")

        return sessionless_tokens_data(tokens)

    async def direct_flow(self, username: str, password: str) -> TokensData:
        conf = await self._config.openid_configuration()

        params = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": self._client.client_id,
            "scope": "openid",
        }

        if isinstance(self._client, PrivateClient):
            params["client_secret"] = self._client.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint, data=params) as resp:
                status = resp.status
                token = await resp.json()
                if status != 200:
                    raise RuntimeError(f"Failed to get token : {token}")
        return tokens_data(token)

    async def token_exchange(
        self, requested_subject: str, subject_token: str
    ) -> TokensData:
        conf = await self._config.openid_configuration()

        params = {
            "client_id": self._client.client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "requested_subject": requested_subject,
        }

        if isinstance(self._client, PrivateClient):
            params["client_secret"] = self._client.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint, data=params) as resp:
                status = resp.status
                token = await resp.json()
                if status != 200:
                    raise RuntimeError(f"Failed to exchange token : {token}")

        return tokens_data(token)

    async def refresh(self, refresh_token: str) -> TokensData:
        conf = await self._config.openid_configuration()

        params = {
            "client_id": self._client.client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "openid",
        }

        if isinstance(self._client, PrivateClient):
            params["client_secret"] = self._client.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(conf.token_endpoint, data=params) as resp:
                status = resp.status
                tokens = await resp.json()
                if status != 200:
                    raise RuntimeError(f"Failed to refresh token : {tokens}")

        return tokens_data(tokens)

    async def logout_url(self, redirect_uri: str, state: str) -> str:
        conf = await self._config.openid_configuration()
        url = URL(conf.end_session_endpoint)
        return str(
            url.replace_query_params(
                post_logout_redirect_uri=redirect_uri,
                client_id=self._client.client_id,
                state=state,
            )
        )

    async def token_decode(self, token: str) -> Dict[str, Any]:
        return await self._config.token_decode(token)

    def client_id(self) -> str:
        return self._client.client_id
