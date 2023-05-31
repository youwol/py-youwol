# standard library
import uuid

# typing
from typing import Callable, Optional, Tuple

# Youwol utilities
from youwol.utils import CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient
from youwol.utils.clients.oidc.tokens import (
    Tokens,
    restore_tokens_from_session_id,
    save_tokens,
)

# relative
from .openid_flows_states import AuthorizationFlow, LogoutFlow


class FlowStateNotFound(RuntimeError):
    def __init__(self):
        super().__init__("Flow state not found")


class OpenidFlowsService:
    def __init__(
        self,
        cache: CacheClient,
        oidc_client: OidcForClient,
        tokens_id_generator: Callable[[], str],
    ):
        self.__cache = cache
        self.__oidc_client = oidc_client
        self.__tokens_id_generator = tokens_id_generator

    async def init_authorization_flow(
        self, target_uri: str, login_hint: Optional[str], callback_uri: str
    ) -> str:
        flow_uuid = str(uuid.uuid4())

        url, code_verifier = await self.__oidc_client.auth_flow_url(
            state=flow_uuid, redirect_uri=callback_uri, login_hint=login_hint
        )

        flow_state = AuthorizationFlow(
            uuid=flow_uuid,
            cache=self.__cache,
            target_uri=target_uri,
            code_verifier=code_verifier,
        )
        flow_state.save()

        return url

    async def handle_authorization_flow_callback(
        self, flow_uuid: str, code: str, callback_uri: str
    ) -> Tuple[Tokens, str]:
        flow_state_data = self.__cache.get(AuthorizationFlow.cache_key(flow_uuid))

        if flow_state_data is None:
            raise FlowStateNotFound()

        flow_state = AuthorizationFlow(cache=self.__cache, **flow_state_data)

        code_verifier = flow_state.code_verifier
        target_uri = flow_state.target_uri
        flow_state.delete()

        tokens_data = await self.__oidc_client.auth_flow_handle_cb(
            code=code, code_verifier=code_verifier, redirect_uri=callback_uri
        )

        tokens = await save_tokens(
            tokens_id=self.__tokens_id_generator(),
            cache=self.__cache,
            oidc_client=self.__oidc_client,
            **tokens_data,
        )

        return tokens, target_uri

    async def direct_auth_flow(self, username: str, password: str) -> Tokens:
        tokens_data = await self.__oidc_client.direct_flow(
            username=username, password=password
        )

        return await save_tokens(
            tokens_id=self.__tokens_id_generator(),
            cache=self.__cache,
            oidc_client=self.__oidc_client,
            **tokens_data,
        )

    async def init_logout_flow(
        self, target_uri: str, forget_me: bool, callback_uri: str
    ):
        logout_flow_state = LogoutFlow(
            uuid=str(uuid.uuid4()),
            target_uri=target_uri,
            forget_me=forget_me,
            cache=self.__cache,
        )
        logout_flow_state.save()

        url = await self.__oidc_client.logout_url(
            state=logout_flow_state.uuid, redirect_uri=callback_uri
        )

        return url

    def handle_logout_flow_callback(self, flow_uuid):
        flow_state_data = self.__cache.get(LogoutFlow.cache_key(flow_uuid))

        if flow_state_data is None:
            raise FlowStateNotFound()

        flow_state = LogoutFlow(cache=self.__cache, **flow_state_data)
        target_uri = flow_state.target_uri
        forget_me = flow_state.forget_me
        flow_state.delete()

        return target_uri, forget_me

    async def handle_logout_back_channel(self, logout_token: str):
        logout_token_decoded = await self.__oidc_client.token_decode(logout_token)
        # TODO : validate logout token (see https://openid.net/specs/openid-connect-backchannel-1_0.html#Validation)
        tokens = restore_tokens_from_session_id(
            session_id=logout_token_decoded["sid"],
            cache=self.__cache,
            oidc_client=self.__oidc_client,
        )
        await tokens.delete()
