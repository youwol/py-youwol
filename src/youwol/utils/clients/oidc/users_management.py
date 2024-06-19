# standard library
import time

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient
from youwol.utils.clients.oidc.service_account_client import ServiceAccountClient

TWELVE_HOURS = 12 * 60 * 60

# Visitor creation attributes
USER_ATTR_TEMP_USER = "temporary_user"
USER_ATTR_TEMP_USER_IP = "temporary_user_ip"
USER_ATTR_TEMP_USER_USER_AGENT = "temporary_user_user_agent"
USER_ATTR_TEMP_USER_TIMESTAMP = "temporary_user_timestamp"

# User creation pending attributes
USER_ATTR_REG_PENDING = "registration_pending"
USER_ATTR_REG_PENDING_IP = "registration_pending_ip"
USER_ATTR_REG_PENDING_USER_AGENT = "registration_pending_user_agent"
USER_ATTR_REG_PENDING_TIMESTAMP = "registration_pending_timestamp"

# User creation finalization attributes
USER_ATTR_FINAL_IP = "finalization_ip"
USER_ATTR_FINAL_USER_AGENT = "finalization_user_agent"
USER_ATTR_FINAL_TIMESTAMP = "finalization_timestamp"

# In case no value in existing user attributes
USER_ATTR_TEMP_USER_IP_UNSET = "TEMPORARY_USER_IP_UNSET"
USER_ATTR_TEMP_USER_USER_AGENT_UNSET = "TEMPORARY_USER_USER_AGENT_UNSET"
USER_ATTR_TEMP_USER_TIMESTAMP_UNSET = "TEMPORARY_USER_TIMESTAMP_UNSET"
USER_ATTR_REG_PENDING_IP_UNSET = "REGISTRATION_PENDING_IP_UNSET"
USER_ATTR_REG_PENDING_USER_AGENT_UNSET = "REGISTRATION_PENDING_USER_AGENT_UNSET"
USER_ATTR_REG_PENDING_TIMESTAMP_UNSET = "REGISTRATION_PENDING_TIMESTAMP_UNSET"


class UserBriefRepresentation(BaseModel):
    id: str
    username: str
    createdTimestamp: int


class UserRepresentation(UserBriefRepresentation):
    attributes: dict[str, list[str]] = {}


class KeycloakUsersManagement(ServiceAccountClient):
    _SERVICE_ACCOUNT_TOKEN_CACHE_KEY = "keycloak_user_management_token"

    def __init__(self, realm_url: str, cache: CacheClient, oidc_client: OidcForClient):
        super().__init__(base_url=realm_url, cache=cache, oidc_client=oidc_client)

    async def get_temporary_users(
        self, first: int = 0
    ) -> list[UserBriefRepresentation]:
        return await self.get_users_with_query(q="temporary_user:true", first=first)

    async def get_users_with_query(
        self, q: str, first: int = 0
    ) -> list[UserBriefRepresentation]:
        return [
            UserBriefRepresentation.parse_obj(item)
            for item in (
                await self._get(
                    path="/users",
                    params={"briefRepresentation": "true", "q": q, "first": first},
                )
            )
        ]

    async def count_users(self, q: str = ""):
        params = {"q": q} if q else {}
        return await self._get(path="/users/count", params=params)

    async def get_user_detail(self, user_id: str) -> UserRepresentation:
        obj = await self._get(path=f"/users/{user_id}")
        return UserRepresentation.parse_obj(obj)

    async def create_user(
        self, username: str, password: str, ip: str, user_agent: str
    ) -> None:
        await self._post(
            path="/users",
            json={
                "username": username,
                "email": username,
                "emailVerified": True,
                "enabled": True,
                "attributes": {
                    USER_ATTR_TEMP_USER: True,
                    USER_ATTR_TEMP_USER_IP: ip,
                    USER_ATTR_TEMP_USER_USER_AGENT: user_agent,
                    USER_ATTR_TEMP_USER_TIMESTAMP: int(time.time()),
                },
                "groups": ["youwol-users"],
                "credentials": [
                    {"temporary": False, "type": "password", "value": password}
                ],
            },
        )

    async def delete_user(self, user_id: str) -> None:
        await self._delete(path=f"/users/{user_id}")

    async def register_user(
        self,
        sub: str,
        email: str,
        target_uri: str,
        client_id: str,
        ip: str,
        user_agent: str,
    ) -> None:
        existing_attributes = await self.__get_user_attributes_or_default(
            sub,
            {
                USER_ATTR_TEMP_USER_IP: USER_ATTR_TEMP_USER_IP_UNSET,
                USER_ATTR_TEMP_USER_USER_AGENT: USER_ATTR_TEMP_USER_USER_AGENT_UNSET,
                USER_ATTR_TEMP_USER_TIMESTAMP: USER_ATTR_TEMP_USER_TIMESTAMP_UNSET,
            },
        )
        await self._put(
            f"/users/{sub}",
            json={
                "email": email,
                "emailVerified": False,
                "enabled": True,
                "attributes": {
                    **existing_attributes,
                    USER_ATTR_TEMP_USER: True,
                    USER_ATTR_REG_PENDING: int(time.time()) + TWELVE_HOURS,
                    USER_ATTR_REG_PENDING_IP: ip,
                    USER_ATTR_REG_PENDING_USER_AGENT: user_agent,
                    USER_ATTR_REG_PENDING_TIMESTAMP: int(time.time()),
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

    async def finalize_user(self, sub: str, ip: str, user_agent: str) -> None:
        existing_attributes = await self.__get_user_attributes_or_default(
            sub,
            {
                USER_ATTR_REG_PENDING_IP: USER_ATTR_REG_PENDING_IP_UNSET,
                USER_ATTR_REG_PENDING_TIMESTAMP: USER_ATTR_REG_PENDING_TIMESTAMP_UNSET,
                USER_ATTR_REG_PENDING_USER_AGENT: USER_ATTR_REG_PENDING_USER_AGENT_UNSET,
                USER_ATTR_TEMP_USER_IP: USER_ATTR_TEMP_USER_IP_UNSET,
                USER_ATTR_TEMP_USER_TIMESTAMP: USER_ATTR_TEMP_USER_TIMESTAMP_UNSET,
                USER_ATTR_TEMP_USER_USER_AGENT: USER_ATTR_TEMP_USER_USER_AGENT_UNSET,
            },
        )
        await self._put(
            path=f"/users/{sub}",
            json={
                "attributes": {
                    **existing_attributes,
                    USER_ATTR_FINAL_IP: ip,
                    USER_ATTR_FINAL_USER_AGENT: user_agent,
                    USER_ATTR_FINAL_TIMESTAMP: int(time.time()),
                }
            },
            parse_response=False,
        )

    async def __get_user_attributes_or_default(
        self, sub: str, defaults: dict[str, str]
    ) -> dict[str, str]:
        user_details = await self._get(path=f"/users/{sub}")
        r = defaults
        if "attributes" not in user_details:
            return r

        for k in r:
            if k in user_details["attributes"]:
                r[k] = user_details["attributes"][k]

        return r
