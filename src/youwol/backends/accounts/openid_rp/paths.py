# standard library
import uuid

# typing
from typing import Annotated

# third parties
from fastapi import Cookie, Depends, Form, Header, status
from prometheus_client import Counter
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.status import HTTP_204_NO_CONTENT

# Youwol utilities
from youwol.utils.clients.oidc.service_account_client import UnexpectedResponseStatus
from youwol.utils.servers.request import (
    VALUE_WHEN_REQUEST_HAS_NO_USER_AGENT_HEADER,
    get_real_client_ip,
)

# relative
from ..configuration import Configuration, get_configuration
from ..root_paths import router
from ..utils import url_for
from .openid_flows_service import FlowStateNotFound, InvalidLogoutToken

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60
FIVE_MINUTES_IN_SECONDS = 5 * 60

counter_login_start = Counter("accounts_login_start", "Nb login started")
counter_login_completed = Counter("accounts_login_completed", "Nb login completed")
counter_login_failure = Counter("accounts_login_failure", "Nb login failed")
counter_anonymous = Counter("accounts_visitors_created", "Nb visitor profiles created")


@router.get("/openid_rp/auth")
async def authorization_flow(
    request: Request,
    target_uri: str = "/",
    yw_login_hint: Annotated[str | None, Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
    Initiate an Authorization Code Grant authentification.
    Could be call directly or by /openid_rp/login endpoint
    Must be called by an interactive User Agent (not from script, backend, etc.).
    target_uri must match valid redirect URI as defined in the Identity Provider for the OpenId client
    yw_login_hint is nothing more than a hint (usually the default value for the login form)

    Redirect to the Identity Provider, which will ultimately redirect to /openid_rp/cb endpoint.

    Parameters:
        request: Incoming request.
        target_uri: Target redirection URI.
        yw_login_hint: Login hint.
        conf: Current environment.

    Returns:
        Response from the redirect.
    """
    login_hint = (
        yw_login_hint[5:]
        if yw_login_hint and yw_login_hint.startswith("user:")
        else None
    )

    redirect_uri = await conf.openid_flows.init_authorization_flow(
        target_uri=target_uri,
        login_hint=login_hint,
        callback_uri=url_for(
            request=request,
            function_name="authorization_flow_callback",
            https=conf.https,
        ),
    )

    counter_login_start.inc()

    return RedirectResponse(redirect_uri, status_code=307)


@router.get("/openid_rp/auth/cb")
async def authorization_flow_callback(
    request: Request,
    state: str,
    code: str,
    user_agent: Annotated[str, Header()] = VALUE_WHEN_REQUEST_HAS_NO_USER_AGENT_HEADER,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
    Callback for an ongoing Authorization Code Grant authentification.
    Shall be called by an interactive User Agent after the Identity Provider redirect it.

    Save access token in cookie.
    Also store logged-in user in yw_login_hint (see /openid_rp/login and /openid_rp/auth endpoints).
    Redirect to the target_uri passed to authorization_flow(request, target_uri) − this target_uri is passed
    around in base64 and is in the param state.
    """
    try:
        (
            tokens,
            target_uri,
        ) = await conf.openid_flows.handle_authorization_flow_callback(
            flow_ref=state,
            code=code,
            callback_uri=url_for(
                request=request,
                function_name="authorization_flow_callback",
                https=conf.https,
            ),
        )
        if tokens is None:
            return JSONResponse(
                status_code=400, content={"invalid param": "Invalid state"}
            )

        if await tokens.is_temp():
            if conf.keycloak_users_management is None:
                return JSONResponse(
                    status_code=403,
                    content={"forbidden": "no administration right on the server side"},
                )
            try:
                await conf.keycloak_users_management.finalize_user(
                    sub=await tokens.sub(),
                    ip=get_real_client_ip(request),
                    user_agent=user_agent,
                )
            except UnexpectedResponseStatus as e:
                return JSONResponse(status_code=e.actual, content=e.content)

        await tokens.refresh()

        response = RedirectResponse(url=target_uri, status_code=307)
        response.set_cookie(
            "yw_jwt",
            tokens.id(),
            secure=conf.https,
            httponly=True,
            max_age=tokens.remaining_time(),
        )
        response.set_cookie(
            "yw_login_hint",
            f"user:{await tokens.username()}",
            secure=conf.https,
            httponly=True,
            expires=ONE_YEAR_IN_SECONDS,
        )
        counter_login_completed.inc()
        return response
    except FlowStateNotFound:
        counter_login_failure.inc()
        return JSONResponse(status_code=400, content={"invalid param": "Invalid state"})


@router.get("/openid_rp/logout")
async def logout(
    request: Request,
    target_uri: str,
    forget_me: bool = False,
    yw_jwt: Annotated[str | None, Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
    Logout user.
    Must be call by an interactive User Agent.
    The same rule apply to target_uri as with /openid_rp/auth endpoint

    Delete access token cookie
    Optionally delete yw_login_hint, if forget_me param is true
    Redirect to Identity Provider for logout, which will ultimately redirect to target_uri.
    """
    if yw_jwt is None:
        return JSONResponse(
            status_code=400, content={"invalid auth": "not authenticated"}
        )
    redirect_uri = await conf.openid_flows.init_logout_flow(
        target_uri=target_uri,
        forget_me=forget_me,
        callback_uri=url_for(
            request=request, function_name="logout_cb", https=conf.https
        ),
        tokens_id=yw_jwt,
    )

    return RedirectResponse(url=redirect_uri, status_code=307)


@router.get("/openid_rp/logout/cb")
async def logout_cb(
    state: str,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    target_uri, forget_me = conf.openid_flows.handle_logout_flow_callback(
        flow_ref=state
    )
    response = RedirectResponse(url=target_uri, status_code=307)

    response.set_cookie(
        "yw_jwt", "DELETED", secure=conf.https, httponly=True, expires=0
    )
    response.set_cookie(
        "yw_jwt_t", "DELETED", secure=conf.https, httponly=True, expires=0
    )

    if forget_me:
        response.set_cookie(
            "yw_login_hint",
            "DELETED",
            secure=conf.https,
            httponly=True,
            expires=0,
        )

    return response


@router.post("/openid_rp/logout/back_channel", status_code=HTTP_204_NO_CONTENT)
async def back_channel_logout(
    logout_token: Annotated[str, Form()],
    response: Response,
    conf: Configuration = Depends(get_configuration),
) -> None:
    try:
        await conf.openid_flows.handle_logout_back_channel(logout_token=logout_token)
    except InvalidLogoutToken as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        response.body = str(e).encode(encoding="utf-8")


@router.get("/openid_rp/login")
async def login(
    request: Request,
    target_uri: str,
    flow: str = "auto",
    user_agent: Annotated[str, Header()] = VALUE_WHEN_REQUEST_HAS_NO_USER_AGENT_HEADER,
    yw_login_hint: Annotated[str | None, Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
    Log in user.
    Must be call by an interactive User Agent.
    The same rule apply to target_uri as with /openid_rp/auth endpoint.

    Will either call /openid_rp/auth or /openid_rp/temp_user, based on flow param:
    - 'user' => /openid_rp/auth
    - 'temp' => /openid_rp/temp_user
    - 'auto' (default) =>
            cookie yw_login_hint => /openid_rp/auth
            no cookie yw_login_hint => /openid_rp/temp_user
    """
    if flow == "auto":
        flow = (
            "user"
            if (yw_login_hint or conf.keycloak_users_management is None)
            else "temp"
        )

    if flow == "user":
        return await authorization_flow(request, target_uri, yw_login_hint, conf)

    if flow == "temp":
        return await login_as_temp_user(request, target_uri, user_agent, conf)

    return JSONResponse(status_code=400, content={"invalid request", "unknown flow"})


@router.get("/openid_rp/temp_user")
async def login_as_temp_user(
    request: Request,
    target_uri: str = "/",
    user_agent: Annotated[str, Header()] = VALUE_WHEN_REQUEST_HAS_NO_USER_AGENT_HEADER,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
    Create a temporary user and get an access token for it.
    Could be call directly or by /openid_rp/login endpoint

    Save access token in cookie.
    Redirect to target_path (can be relative to this endpoint URI).
    """
    if conf.keycloak_users_management is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "No administration right on the server side"},
        )

    username = f"support+visitor_{uuid.uuid4()}@youwol.com"
    password = str(uuid.uuid4())
    await conf.keycloak_users_management.create_user(
        username=username,
        password=password,
        ip=get_real_client_ip(request),
        user_agent=user_agent,
    )

    tokens = await conf.openid_flows.direct_auth_flow(
        username=username, password=password
    )

    response = RedirectResponse(url=target_uri, status_code=307)
    response.set_cookie(
        "yw_jwt",
        tokens.id(),
        secure=conf.https,
        httponly=True,
        max_age=tokens.remaining_time(),
    )
    counter_anonymous.inc()
    return response
