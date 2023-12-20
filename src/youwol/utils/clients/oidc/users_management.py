# standard library
import time

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient
from youwol.utils.clients.oidc.service_account_client import ServiceAccountClient

TWELVE_HOURS = 12 * 60 * 60


class User(BaseModel):
    id: str
    username: str


class KeycloakUsersManagement(ServiceAccountClient):
    _SERVICE_ACCOUNT_TOKEN_CACHE_KEY = "keycloak_user_management_token"

    def __init__(self, realm_url: str, cache: CacheClient, oidc_client: OidcForClient):
        super().__init__(base_url=realm_url, cache=cache, oidc_client=oidc_client)

    async def get_temporary_users(self) -> list[User]:
        return [
            User.parse_obj(item)
            for item in (
                await self._get(
                    path="/users",
                    params={"briefRepresentation": "true", "q": "temporary_user:true"},
                )
            )
        ]

    async def create_user(self, username: str, password: str) -> None:
        await self._post(
            path="/users",
            json={
                "username": username,
                "email": username,
                "emailVerified": True,
                "enabled": True,
                "attributes": {"temporary_user": True},
                "groups": ["youwol-users"],
                "credentials": [
                    {"temporary": False, "type": "password", "value": password}
                ],
            },
        )

    async def delete_user(self, user_id: str) -> None:
        await self._delete(path=f"/users/{user_id}")

    async def register_user(
        self, sub: str, email: str, target_uri: str, client_id: str
    ) -> None:
        await self._put(
            f"/users/{sub}",
            json={
                "username": email,
                "email": email,
                "emailVerified": False,
                "enabled": True,
                "attributes": {
                    "temporary_user": True,
                    "registration_pending": int(time.time()) + TWELVE_HOURS,
                },
                "groups": ["youwol-users"],
            },
            parse_response=False,
        )
        await self._put(
            path=f"/users/{sub}/execute-actions-email",
            params={
                "client_id": client_id,
                "redirect_uri": target_uri,
                "lifespan": TWELVE_HOURS,
            },
            json=["UPDATE_PROFILE", "UPDATE_PASSWORD"],
            parse_response=False,
        )

    async def finalize_user(self, sub: str) -> None:
        await self._put(path=f"/users/{sub}", json={"attributes": {}})
