# standard library
import uuid

# typing
from typing import Annotated, Optional

# third parties
from fastapi import Depends
from fastapi.params import Cookie, Form
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.status import HTTP_204_NO_CONTENT

# relative
from ..configuration import Configuration, get_configuration
from ..root_paths import router
from .openid_flows_service import FlowStateNotFound

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60
FIVE_MINUTES_IN_SECONDS = 5 * 60


@router.get("/openid_rp/auth")
async def authorization_flow(
    request: Request,
    target_uri: str,
    yw_login_hint: Annotated[Optional[str], Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
        Initiate an Authorization Code Grant authentification.
        Could be call directly or by /openid_rp/login endpoint
        Must be called by an interactive User Agent (not from script, backend, etc.).
        target_uri must match valid redirect URI as defined in the Identity Provider for the OpenId client
        yw_login_hint is nothing more than a hint (usually the default value for the login form)

        Redirect to the Identity Provider, which will ultimately redirect to /openid_rp/cb endpoint.

    :param request:
    :param target_uri:
    :param yw_login_hint:
    :param conf:
    :return:
    """
    login_hint = (
        yw_login_hint[5:] if yw_login_hint and yw_login_hint[:5] == "user:" else None
    )
    redirect_uri = await conf.openid_flows.init_authorization_flow(
        target_uri=target_uri,
        login_hint=login_hint,
        callback_uri=str(request.url_for("authorization_flow_callback")),
    )

    return RedirectResponse(redirect_uri, status_code=307)


@router.get("/openid_rp/auth/cb")
async def authorization_flow_callback(
    request: Request,
    state: str,
    code: str,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
        Callback for an ongoing Authorization Code Grant authentification.
        Shall be called by an interactive User Agent after the Identity Provider redirect it.

        Save access token in cookie.
        Also store logged-in user in yw_login_hint (see /openid_rp/login and /openid_rp/auth endpoints).
        Redirect to the target_uri passed to authorization_flow(request, target_uri) − this target_uri is passed
        around in base64 and is in the param state.

    :param request:
    :param state:
    :param code:
    :param conf:
    :return:
    """
    try:
        (
            tokens,
            target_uri,
        ) = await conf.openid_flows.handle_authorization_flow_callback(
            flow_uuid=state,
            code=code,
            callback_uri=str(request.url_for("authorization_flow_callback")),
        )
        if tokens is None:
            return JSONResponse(
                status_code=400, content={"invalid param": "Invalid state"}
            )

        response = RedirectResponse(url=target_uri, status_code=307)
        response.set_cookie(
            "yw_jwt",
            tokens.id(),
            secure=conf.secure_cookies,
            httponly=True,
            max_age=tokens.remaining_time(),
        )
        response.set_cookie(
            "yw_login_hint",
            f"user:{await tokens.username()}",
            secure=conf.secure_cookies,
            httponly=True,
            expires=ONE_YEAR_IN_SECONDS,
        )
        return response
    except FlowStateNotFound:
        return JSONResponse(status_code=400, content={"invalid param": "Invalid state"})


@router.get("/openid_rp/logout")
async def logout(
    request: Request,
    target_uri: str,
    forget_me: bool = False,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
        Logout user.
        Must be call by an interactive User Agent.
        The same rule apply to target_uri as with /openid_rp/auth endpoint

        Delete access token cookie
        Optionally delete yw_login_hint, if forget_me param is true
        Redirect to Identity Provider for logout, which will ultimately redirect to target_uri.

    :param request:
    :param target_uri:
    :param forget_me:
    :param conf:
    :return:
    """
    redirect_uri = await conf.openid_flows.init_logout_flow(
        target_uri=target_uri,
        forget_me=forget_me,
        callback_uri=str(request.url_for("logout_cb")),
    )

    return RedirectResponse(url=redirect_uri, status_code=307)


@router.get("/openid_rp/logout/cb")
async def logout_cb(
    state: str,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    target_uri, forget_me = conf.openid_flows.handle_logout_flow_callback(
        flow_uuid=state
    )

    response = RedirectResponse(url=target_uri, status_code=307)

    response.set_cookie(
        "yw_jwt", "DELETED", secure=conf.secure_cookies, httponly=True, expires=0
    )
    response.set_cookie(
        "yw_jwt_t", "DELETED", secure=conf.secure_cookies, httponly=True, expires=0
    )

    if forget_me:
        response.set_cookie(
            "yw_login_hint",
            "DELETED",
            secure=conf.secure_cookies,
            httponly=True,
            expires=0,
        )

    return response


@router.post("/openid_rp/logout/back_channel", status_code=HTTP_204_NO_CONTENT)
async def back_channel_logout(
    logout_token: Annotated[str, Form()],
    conf: Configuration = Depends(get_configuration),
) -> None:
    await conf.openid_flows.handle_logout_back_channel(logout_token=logout_token)


@router.get("/openid_rp/login")
async def login(
    request: Request,
    target_uri: str,
    flow: str = "auto",
    yw_login_hint: Annotated[Optional[str], Cookie()] = None,
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

    :param request:
    :param target_uri:
    :param flow:
    :param yw_login_hint:
    :param conf:
    :return:
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
        return await login_as_temp_user(target_uri, conf)

    return JSONResponse(status_code=400, content={"invalid request", "unknown flow"})


@router.get("/openid_rp/temp_user")
async def login_as_temp_user(
    target_uri: str = "/",
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
        Create a temporary user and get an access token for it.
        Could be call directly or by /openid_rp/login endpoint

        Save access token in cookie.
        Redirect to target_path (can be relative to this endpoint URI)

    :param target_uri:
    :param conf:
    :return:
    """
    if conf.keycloak_users_management is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "No administration right on the server side"},
        )

    user_name = f"{uuid.uuid4()}@temp.youwol.com"
    password = str(uuid.uuid4())
    await conf.keycloak_users_management.create_user(user_name, password)

    tokens = await conf.openid_flows.direct_auth_flow(
        username=user_name, password=password
    )

    response = RedirectResponse(url=target_uri, status_code=307)
    response.set_cookie(
        "yw_jwt",
        tokens.id(),
        secure=conf.secure_cookies,
        httponly=True,
        max_age=tokens.remaining_time(),
    )
    return response
