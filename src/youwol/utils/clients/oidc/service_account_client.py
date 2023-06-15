# standard library
import datetime

# typing
from typing import Any, Dict, Optional

# third parties
import aiohttp

from starlette.datastructures import URL

# Youwol utilities
from youwol.utils import AT, CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient


class UnexpectedResponseStatus(RuntimeError):
    def __init__(self, expected: int, actual: int, content: Any):
        super().__init__(f"Expecting response status {expected}, got {actual}")
        self.actual = actual
        self.content = content


class ServiceAccountClient:
    _SESSIONLESS_TOKEN_EXPIRES_AT_THRESHOLD = 15
    _SERVICE_ACCOUNT_TOKEN_CACHE_KEY = "keycloak_user_management_token"

    def __init__(
        self,
        cache: CacheClient,
        oidc_client: OidcForClient,
        base_url: Optional[str] = None,
    ):
        self.__base_url = base_url
        self.__oidc_client = oidc_client
        self.__cache = cache

    async def __get_access_token(self) -> str:
        now = datetime.datetime.now().timestamp()
        token_data = self.__cache.get(self._SERVICE_ACCOUNT_TOKEN_CACHE_KEY)
        if token_data is None or int(token_data["expires_at"]) < int(now):
            sessionless_tokens_data = await self.__oidc_client.client_credentials_flow()
            expires_at = (
                int(now)
                + sessionless_tokens_data.expires_in
                - self._SESSIONLESS_TOKEN_EXPIRES_AT_THRESHOLD
            )
            token_data = {
                "access_token": sessionless_tokens_data.access_token,
                "expires_at": expires_at,
            }
            self.__cache.set(
                self._SERVICE_ACCOUNT_TOKEN_CACHE_KEY,
                token_data,
                AT(expires_at),
            )

        return str(token_data["access_token"])

    async def __request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
        parse_response=True,
    ) -> Optional[Any]:
        token = await self.__get_access_token()
        url = URL(f"{self.__base_url if self.__base_url else ''}{path}")
        if params:
            url = url.replace_query_params(**params)
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.request(
                method=method, url=str(url), params=params, json=json
            ) as resp:
                if resp.status != expected_status:
                    if resp.content_type == "application/json":
                        content = await resp.json()
                    else:
                        content = await resp.text()
                    raise UnexpectedResponseStatus(
                        expected=expected_status,
                        actual=resp.status,
                        content=content,
                    )
                if parse_response:
                    return await resp.json()
                return None

    async def _get(self, path: str, params: Dict[str, Any]):
        return await self.__request(method="GET", path=path, params=params)

    async def _put(
        self,
        path: str,
        json: Any,
        params: Optional[Dict[str, Any]] = None,
        expected_status: int = 204,
    ):
        return await self.__request(
            method="PUT",
            path=path,
            params=params,
            json=json,
            expected_status=expected_status,
        )

    async def _post(
        self,
        path: str,
        json: Any,
        expected_status: int = 201,
        parse_response: bool = False,
    ):
        return await self.__request(
            method="POST",
            path=path,
            json=json,
            expected_status=expected_status,
            parse_response=parse_response,
        )

    async def _delete(
        self, path: str, expected_status: int = 204, parse_response: bool = False
    ):
        return await self.__request(
            method="DELETE",
            path=path,
            expected_status=expected_status,
            parse_response=parse_response,
        )
