# standard library
import base64
import datetime
import hashlib
import secrets

from dataclasses import dataclass

# typing
from typing import Any, Dict, List, Optional, Tuple, Union

# third parties
import aiohttp
import jwt

from aiohttp import BasicAuth
from jwt import PyJWKClient
from pydantic import BaseModel
from starlette.datastructures import URL

DEFAULT_LENGTH_RANDOM_TOKEN = 64
EXPIRATION_THRESHOLD = 60


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
    expires_at: float
    refresh_expires_at: float
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

    now = datetime.datetime.now().timestamp()
    return TokensData(
        id_token=str(data["id_token"]),
        access_token=str(data["access_token"]),
        refresh_token=str(data["refresh_token"]),
        expires_at=now - EXPIRATION_THRESHOLD + int(data["expires_in"]),
        refresh_expires_at=now - EXPIRATION_THRESHOLD + int(data["refresh_expires_in"]),
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
                    json = await resp.json()
            self._openid_configuration = OpenIdConfiguration.parse_obj(json)

        return self._openid_configuration


class OidcForClient:
    def __init__(self, config: OidcConfig, client: Client) -> None:
        self.__config = config
        self.__client = client

    async def __post_token_endpoint(self, **params) -> Any:
        conf = await self.__config.openid_configuration()
        auth = None
        if isinstance(self.__client, PrivateClient):
            auth = BasicAuth(
                login=self.__client.client_id, password=self.__client.client_secret
            )
        else:
            params = self.__params_with_client_id(**params)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.post(url=conf.token_endpoint, data=params) as resp:
                status = resp.status
                if status != 200:
                    if resp.content_type == "application/json":
                        content = await resp.json()
                    else:
                        content = await resp.text()
                    raise RuntimeError(f"Unexpected HTTP status {status} : {content}")
                return await resp.json()

    def __params_with_client_id(self, **params) -> Dict[str, Any]:
        return {**params, "client_id": self.__client.client_id}

    async def auth_flow_url(
        self, state: str, redirect_uri: str, login_hint: Optional[str]
    ) -> Tuple[str, str, str]:
        """OpenId Authorization Code Flow request URL

        See:
            * OpenId Authorization Code Flow : https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth
            * Authentication Request : https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest
            * Proof Key for Code Exchange : https://datatracker.ietf.org/doc/html/rfc7636
            * Nonce implementations notes : https://openid.net/specs/openid-connect-core-1_0.html#NonceNotes

        Args:
            state (str): opaque value, to maintain state between this request ond the callback
            redirect_uri (str): the callback URL where the response will be send (by redirecting the User Agent once
                                User is authenticated)
            login_hint (Union[None, None, None, str, None, None]): username to pre-fill login form.

        Returns:
            Tuple[str, str, str]:
                * the URL to request End-User authentication
                * the code verifier for PKCE
                * the ID token nonce for mitigating replay attacks
        """

        conf = await self.__config.openid_configuration()
        url = URL(conf.authorization_endpoint)

        # PKCE (Proof Key for Code Exchange)
        # See https://datatracker.ietf.org/doc/html/rfc7636
        code_verifier = secrets.token_urlsafe(DEFAULT_LENGTH_RANDOM_TOKEN)
        hash_code_verifier = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(hash_code_verifier)
            .decode("ascii")
            .replace("=", "")
        )

        # Nonce, to be checked in ID token.
        # See https://openid.net/specs/openid-connect-core-1_0.html#NonceNotes
        nonce = secrets.token_urlsafe(DEFAULT_LENGTH_RANDOM_TOKEN)

        params = self.__params_with_client_id(
            response_type="code",
            state=state,
            scope="openid",
            redirect_uri=redirect_uri,
            login_hint=login_hint,
            # Nonce
            nonce=nonce,
            # PKCE
            code_challenge_method="S256",
            code_challenge=code_challenge,
        )
        # Remove login_hint if None
        params = {k: v for k, v in params.items() if v is not None}

        return str(url.replace_query_params(**params)), code_verifier, nonce

    async def auth_flow_handle_cb(
        self, code: str, redirect_uri: str, code_verifier: str, nonce: str
    ) -> TokensData:
        """Authorization Code Flow callback handler

        See:
            * OpenId Authorization Code Flow : https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth
            * Token Request : https://openid.net/specs/openid-connect-core-1_0.html#TokenRequest
            * Proof Key for Code Exchange : https://datatracker.ietf.org/doc/html/rfc7636
            * Nonce implementations notes : https://openid.net/specs/openid-connect-core-1_0.html#NonceNotes

        Args:
            code (str): passed as query param by the Authorization Server
            redirect_uri (str): must match the redirect_uri used in Authorization Code Flow request URL
            code_verifier (str): the code verifier for PKCE
            nonce (str): the ID token nonce for mitigating replay attacks

        Returns:
            TokensData: representation of tokens issued by the Authorization Server
        """
        data = await self.__post_token_endpoint(
            code=code,
            grant_type="authorization_code",
            redirect_uri=redirect_uri,
            # PKCE
            code_verifier=code_verifier,
        )
        result = tokens_data(data)

        # Check ID token nonce
        # See https://openid.net/specs/openid-connect-core-1_0.html#NonceNotes
        id_token_decoded = await self.token_decode(result.id_token)
        if id_token_decoded["nonce"] != nonce:
            raise RuntimeError("Invalid nonce in ID token")

        return result

    async def client_credentials_flow(self) -> SessionlessTokensData:
        """Client Credentials flow

        See https://datatracker.ietf.org/doc/html/rfc6749#section-4.4

        Raises:
            RuntimeError, if the client is public

        Returns:
            SessionlessTokensData: representation of access token issued by the Authorization Server
        """
        if isinstance(self.__client, PublicClient):
            raise RuntimeError(f"Client {self.__client.client_id} is public !")
        data = await self.__post_token_endpoint(grant_type="client_credentials")
        return sessionless_tokens_data(data)

    async def direct_flow(self, username: str, password: str) -> TokensData:
        """Direct Authentication flow

            See https://datatracker.ietf.org/doc/html/rfc6749#section-4.3

        Args:
            username (str): the username
            password (str): the password

        Returns:
            TokensData: representation of tokens issued by the Authorization Server
        """
        data = await self.__post_token_endpoint(
            grant_type="password", username=username, password=password, scope="openid"
        )
        return tokens_data(data)

    async def impersonation(
        self, requested_subject: str, subject_token: str
    ) -> TokensData:
        """Token exchange for impersonation

        See https://www.keycloak.org/docs/latest/securing_apps/#impersonation

        Args:
            requested_subject (str): the sub of the User to impersonate
            subject_token (str): access token for the real User

        Returns:
           TokensData: representation of tokens issued by the Authorization Server
        """
        data = await self.__post_token_endpoint(
            grant_type="urn:ietf:params:oauth:grant-type:token-exchange",
            subject_token=subject_token,
            requested_subject=requested_subject,
            requested_token_type="urn:ietf:params:oauth:token-type:access_token",
        )

        return tokens_data(data)

    async def refresh(self, refresh_token: str) -> TokensData:
        """Refresh tokens

        See https://openid.net/specs/openid-connect-core-1_0.html#RefreshTokens

        Args:
            refresh_token (str): the refresh token

        Returns:
           TokensData: representation of tokens issued by the Authorization Server
        """
        data = await self.__post_token_endpoint(
            grant_type="refresh_token", scope="openid", refresh_token=refresh_token
        )

        return tokens_data(data)

    async def logout_url(
        self, redirect_uri: str, state: str, id_token_hint: Optional[str] = None
    ) -> str:
        """RP-Initiated Logout URL

        See https://openid.net/specs/openid-connect-rpinitiated-1_0.html#RPLogout

        Args:
            redirect_uri (str): the callback URI to which redirect the User Agent after log-out has been performed
            state (str): opaque value, to maintain state between this request ond the callback

        Returns:
            str: the log-out URL
        """
        conf = await self.__config.openid_configuration()
        url = URL(conf.end_session_endpoint)
        return str(
            url.replace_query_params(
                **self.__params_with_client_id(
                    post_logout_redirect_uri=redirect_uri,
                    state=state,
                    id_token_hint=id_token_hint,
                )
            )
        )

    async def token_decode(self, token: str) -> Dict[str, Any]:
        return await self.__config.token_decode(token)

    def client_id(self) -> str:
        return self.__client.client_id
