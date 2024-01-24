# standard library
import base64
import datetime
import hashlib
import secrets

from dataclasses import dataclass

# typing
from typing import Any, Optional, Union

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
    """
    PrivateClient represents a client in the OpenID Connect protocol with a client secret.
    """

    client_id: str
    """
    The client identifier.
    """
    client_secret: str
    """
    The client secret.
    """


class PublicClient(BaseModel):
    """
    Represents a client in the OpenID Connect protocol without a client secret.
    """

    client_id: str
    """
    The client identifier.
    """


class OpenIdConfiguration(BaseModel):
    """
    Represents the OpenID Connect configuration received from the Authorization Server.
    """

    token_endpoint_auth_signing_alg_values_supported: list[str]
    """
    The supported signing algorithms for token endpoint authentication.
    """
    authorization_endpoint: str
    """
    The authorization endpoint URL.
    """
    token_endpoint: str
    """
    The token endpoint URL.
    """
    end_session_endpoint: str
    """
     The end session endpoint URL.
     """
    jwks_uri: str
    """
    The JSON Web Key Set (JWKS) endpoint URL.
    """


class InvalidTokensData(RuntimeError):
    def __init__(self, msg: str) -> None:
        super().__init__(f"Invalid tokens data: {msg}")


@dataclass(frozen=True)
class TokensData:
    """
    Represents the data associated with tokens in the OpenID Connect protocol.
    """

    id_token: str
    """
    The ID token issued by the Authorization Server.
    """
    access_token: str
    """
    The access token used to access protected resources.
    """
    refresh_token: str
    """
    The refresh token used to obtain a new access token.
    """
    expires_at: float
    """
    The expiration timestamp of the access token.
    """
    refresh_expires_at: float
    """
    The expiration timestamp of the refresh token.
    """
    session_state: str
    """
    The session state identifier.
    """


def tokens_data(data: Any) -> TokensData:
    """
    Convert raw token data received from the Authorization Server into a TokensData object.

    Parameters:
        data: Raw token data received from the Authorization Server.

    Returns:
        TokensData object representing the parsed token data.

    Raises:
        InvalidTokensData: If the provided data is missing required attributes or has invalid values.
    """

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
    """
    Immutable data class representing tokens obtained without a session.
    """

    access_token: str
    """
    The access token.
    """
    expires_in: int
    """
    The time, in seconds, until the access token expires.
    """


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
"""
Generic client type (either public - no secret required -,  or private - secret required -).
"""


class OidcInfos(BaseModel):
    """
    Data class representing information related to OpenID Connect (OIDC).
    """

    base_uri: str
    """
    The base URI for OIDC.
    """

    client: Client
    """
    The client information.
    """


class OidcConfig:
    """
    OidcConfig represents the configuration for OpenID Connect (OIDC) in a client application.
    """

    base_url: str
    """
    The base URL for the OIDC configuration.
    """
    _openid_configuration: Optional[OpenIdConfiguration]
    """
    OpenId configuration.
    Initialized at first call of
    [openid_configuration](@yw-nav-meth:youwol.utils.clients.oidc.oidc_config.OidcConfig.openid_configuration)
    """

    _jwks_client: Optional[PyJWKClient]
    """
    JSON Web Key Set (JWKS) client.
    Initialized at first call of
    [jwks_client](@yw-nav-meth:youwol.utils.clients.oidc.oidc_config.OidcConfig.jwks_client)
    """

    def __init__(self, base_url: str):
        """
        Initialize the OidcConfig instance with the specified base URL.

        Parameters:
            base_url: The base URL for the OIDC configuration.
        """
        self.base_url = base_url
        self._jwks_client = None
        self._openid_configuration = None

    def for_client(self, client: Client) -> "OidcForClient":
        """
        Create an OidcForClient instance associated with this configuration.

        Parameters:
            client: The OIDC client.

        Return:
            An instance of OidcForClient.
        """
        return OidcForClient(self, client)

    async def token_decode(self, token: str) -> dict[str, Any]:
        """
        Decode a token and return its JSON representation.

        Args:
            token: The token to decode.

        Returns:
            The JSON representation of the token.
        """
        jwks_client = await self.jwks_client()
        token_data = jwt.decode(
            jwt=token,
            key=jwks_client.get_signing_key_from_jwt(token).key,
            algorithms=await self.jwt_algos(),
            options={"verify_aud": False},
        )
        return token_data

    async def jwt_algos(self) -> list[str]:
        """
        Retrieve the supported JSON Web Token (JWT) algorithms from the OpenID Configuration.

        Return:
            A list of supported JWT algorithms.
        """
        conf = await self.openid_configuration()
        return conf.token_endpoint_auth_signing_alg_values_supported

    async def jwks_client(self) -> PyJWKClient:
        """
        Retrieve or create a JSON Web Key Set (JWKS) client.

        Return:
            PyJWKClient: The JWKS client.
        """
        if self._jwks_client is None:
            conf = await self.openid_configuration()
            self._jwks_client = PyJWKClient(conf.jwks_uri)
        return self._jwks_client

    async def openid_configuration(self) -> OpenIdConfiguration:
        """
        Retrieve or fetch the OpenID Configuration.

        Return:
            OpenIdConfiguration: The OpenID Configuration.

        """
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
    """
    OidcForClient provides methods for interacting with the OpenID Connect (OIDC) protocol
    in the context of a client application.
    """

    def __init__(self, config: OidcConfig, client: Client) -> None:
        """
        Initialize the instance with the provided configuration and client.

        Parameters:
            config: The OIDC configuration.
            client: The OIDC client.
        """
        self.__config = config
        self.__client = client

    def get_base_url(self) -> str:
        return self.__config.base_url

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

    def __params_with_client_id(self, **params) -> dict[str, Any]:
        return {**params, "client_id": self.__client.client_id}

    async def auth_flow_url(
        self, state: str, redirect_uri: str, login_hint: Optional[str]
    ) -> tuple[str, str, str]:
        """
        Generate the URL for the OpenID Authorization Code Flow request.

        See:
            * OpenId Authorization Code Flow : https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth
            * Authentication Request : https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest
            * Proof Key for Code Exchange : https://datatracker.ietf.org/doc/html/rfc7636
            * Nonce implementations notes : https://openid.net/specs/openid-connect-core-1_0.html#NonceNotes

        Parameters:
            state: opaque value, to maintain state between this request and the callback
            redirect_uri: the callback URL where the response will be sent (by redirecting the User Agent once
                                User is authenticated)
            login_hint: username to pre-fill login form.

        Return:
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
        """
        Handle the callback for the OpenID Authorization Code Flow.

        See:
            * OpenId Authorization Code Flow : https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth
            * Token Request : https://openid.net/specs/openid-connect-core-1_0.html#TokenRequest
            * Proof Key for Code Exchange : https://datatracker.ietf.org/doc/html/rfc7636
            * Nonce implementations notes : https://openid.net/specs/openid-connect-core-1_0.html#NonceNotes

        Parameters:
            code: passed as query param by the Authorization Server
            redirect_uri: must match the redirect_uri used in Authorization Code Flow request URL
            code_verifier: the code verifier for PKCE
            nonce: the ID token nonce for mitigating replay attacks

        Return:
            representation of tokens issued by the Authorization Server
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
        """
        Perform the Client Credentials flow.

        See https://datatracker.ietf.org/doc/html/rfc6749#section-4.4

        Return:
            representation of access token issued by the Authorization Server

        Raises:
            RuntimeError: if the client is public

        """
        if isinstance(self.__client, PublicClient):
            raise RuntimeError(f"Client {self.__client.client_id} is public !")
        data = await self.__post_token_endpoint(grant_type="client_credentials")
        return sessionless_tokens_data(data)

    async def direct_flow(self, username: str, password: str) -> TokensData:
        """
        Perform the Direct Authentication flow.

        See https://datatracker.ietf.org/doc/html/rfc6749#section-4.3

        Parameters:
            username: the username
            password: the password

        Return:
            representation of tokens issued by the Authorization Server
        """
        data = await self.__post_token_endpoint(
            grant_type="password", username=username, password=password, scope="openid"
        )
        return tokens_data(data)

    async def impersonation(
        self, requested_subject: str, subject_token: str
    ) -> TokensData:
        """
        Perform token exchange for impersonation.

        See https://www.keycloak.org/docs/latest/securing_apps/#impersonation

        Parameters:
            requested_subject: the sub of the User to impersonate
            subject_token: access token for the real User

        Return:
           representation of tokens issued by the Authorization Server
        """
        data = await self.__post_token_endpoint(
            grant_type="urn:ietf:params:oauth:grant-type:token-exchange",
            subject_token=subject_token,
            requested_subject=requested_subject,
            requested_token_type="urn:ietf:params:oauth:token-type:access_token",
        )

        return tokens_data(data)

    async def refresh(self, refresh_token: str) -> TokensData:
        """
        Refresh tokens using a refresh token.

        See https://openid.net/specs/openid-connect-core-1_0.html#RefreshTokens

        Parameters:
            refresh_token: the refresh token

        Return:
           representation of tokens issued by the Authorization Server
        """
        data = await self.__post_token_endpoint(
            grant_type="refresh_token", scope="openid", refresh_token=refresh_token
        )

        return tokens_data(data)

    async def logout_url(
        self, redirect_uri: str, state: str, id_token_hint: Optional[str] = None
    ) -> str:
        """
        Generate the RP-Initiated Logout URL.

        See https://openid.net/specs/openid-connect-rpinitiated-1_0.html#RPLogout

        Parameters:
            redirect_uri: the callback URI to which redirect the User Agent after log-out has been performed
            state: opaque value, to maintain state between this request ond the callback
            id_token_hint: token hint

        Return:
            the log-out URL
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

    async def token_decode(self, token: str) -> dict[str, Any]:
        """
        Decode a token and return its JSON representation.

        Parameters:
            token: token to decode

        Return:
             The JSON representation of the token
        """
        return await self.__config.token_decode(token)

    def client_id(self) -> str:
        """
        Retrieve the client ID associated with the client.

        Return:
             The client ID.
        """
        return self.__client.client_id
