# typing
from typing import Callable, Optional

# Youwol utilities
from youwol.utils import CacheClient
from youwol.utils.clients.oidc.oidc_config import OidcForClient
from youwol.utils.clients.oidc.tokens_manager import (
    Tokens,
    TokensManager,
    TokensStorage,
)

# relative
from .openid_flows_states import AuthorizationFlow, Flow, LogoutFlow


class InvalidLogoutToken(RuntimeError):
    def __init__(self, msg: str) -> None:
        super().__init__(f"Logout token is invalid: {msg}")


class FlowStateNotFound(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Flow state not found")


class TokenNotFound(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Token not found")


class OpenidFlowsService:
    def __init__(
        self,
        cache: CacheClient,
        tokens_storage: TokensStorage,
        oidc_client: OidcForClient,
        tokens_id_generator: Callable[[], str],
    ):
        self.__cache = cache
        self.__oidc_client = oidc_client
        self.__tokens_manager = TokensManager(
            storage=tokens_storage, oidc_client=self.__oidc_client
        )
        self.__tokens_id_generator = tokens_id_generator

    async def init_authorization_flow(
        self, target_uri: str, login_hint: Optional[str], callback_uri: str
    ) -> str:
        auth_flow_ref = Flow.random_ref()

        url, code_verifier, nonce = await self.__oidc_client.auth_flow_url(
            state=auth_flow_ref, redirect_uri=callback_uri, login_hint=login_hint
        )

        auth_flow = AuthorizationFlow(
            ref=auth_flow_ref,
            cache=self.__cache,
            target_uri=target_uri,
            code_verifier=code_verifier,
            nonce=nonce,
        )
        auth_flow.save()

        return url

    async def handle_authorization_flow_callback(
        self, flow_ref: str, code: str, callback_uri: str
    ) -> tuple[Tokens, str]:
        flow_cache_key = AuthorizationFlow.cache_key(flow_ref)
        flow_state_data = self.__cache.get(flow_cache_key)

        if not isinstance(flow_state_data, dict):
            raise ValueError(f"Cached value for key {flow_cache_key} is not a `dict`")

        if flow_state_data is None:
            raise FlowStateNotFound()

        flow_state = AuthorizationFlow(cache=self.__cache, **flow_state_data)

        code_verifier = flow_state.code_verifier
        target_uri = flow_state.target_uri
        flow_state.delete()

        tokens_data = await self.__oidc_client.auth_flow_handle_cb(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=callback_uri,
            nonce=flow_state.nonce,
        )

        tokens = await self.__tokens_manager.save_tokens(
            tokens_id=self.__tokens_id_generator(),
            tokens_data=tokens_data,
        )

        return tokens, target_uri

    async def direct_auth_flow(self, username: str, password: str) -> Tokens:
        tokens_data = await self.__oidc_client.direct_flow(
            username=username, password=password
        )

        return await self.__tokens_manager.save_tokens(
            tokens_id=self.__tokens_id_generator(),
            tokens_data=tokens_data,
        )

    async def init_logout_flow(
        self, target_uri: str, forget_me: bool, callback_uri: str, tokens_id: str
    ) -> str:
        logout_flow_ref = Flow.random_ref()
        logout_flow = LogoutFlow(
            ref=logout_flow_ref,
            target_uri=target_uri,
            forget_me=forget_me,
            cache=self.__cache,
        )
        logout_flow.save()

        tokens = await self.__tokens_manager.restore_tokens(tokens_id=tokens_id)

        if tokens is None:
            raise TokenNotFound()

        url = await self.__oidc_client.logout_url(
            state=logout_flow.ref,
            redirect_uri=callback_uri,
            id_token_hint=tokens.id_token(),
        )

        return url

    def handle_logout_flow_callback(self, flow_ref: str) -> tuple[str, bool]:
        logout_flow_cache_key = LogoutFlow.cache_key(flow_ref)
        flow_state_data = self.__cache.get(logout_flow_cache_key)

        if flow_state_data is None:
            raise FlowStateNotFound()

        if not isinstance(flow_state_data, dict):
            raise ValueError(
                f"Cached value for key {logout_flow_cache_key} is not a `dict`"
            )

        flow_state = LogoutFlow(cache=self.__cache, **flow_state_data)
        target_uri = flow_state.target_uri
        forget_me = flow_state.forget_me
        flow_state.delete()

        return target_uri, forget_me

    async def handle_logout_back_channel(self, logout_token: str) -> None:
        logout_token_decoded = await self.__oidc_client.token_decode(logout_token)

        # See https://openid.net/specs/openid-connect-backchannel-1_0.html#Validation
        expected_events_claim = "http://schemas.openid.net/event/backchannel-logout"
        if "sid" not in logout_token_decoded:
            raise InvalidLogoutToken("no 'sid' claim")
        if "events" not in logout_token_decoded:
            raise InvalidLogoutToken("no 'events' claim")
        if expected_events_claim not in logout_token_decoded["events"]:
            raise InvalidLogoutToken(
                f"'events' claim does not contain member name '{expected_events_claim}'"
            )
        if "nonce" in logout_token_decoded:
            raise InvalidLogoutToken("found 'nonce' claim")

        tokens = await self.__tokens_manager.restore_tokens_from_session_id(
            session_id=logout_token_decoded["sid"],
        )

        if tokens is None:
            raise FlowStateNotFound()

        await tokens.delete()
