import uuid
from typing import Optional

from fastapi import Depends
from fastapi.params import Cookie
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from youwol_accounts.configuration import get_configuration, Configuration
from youwol_accounts.root_paths import router
from youwol_utils import TTL
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.clients.oidc.users_management import KeycloakUsersManagement
from youwol_utils.session_handler import SessionHandler

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60
FIVE_MINUTES_IN_SECONDS = 5 * 60


@router.get('/openid_rp/auth')
async def authorization_flow(
        request: Request,
        target_uri: str,
        yw_login_hint: Optional[str] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
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
    state_uuid = str(uuid.uuid4())
    redirect_uri = request.url_for('authorization_flow_callback')
    login_hint = None
    if yw_login_hint and yw_login_hint[:5] == 'user:':
        login_hint = yw_login_hint[5:]

    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    url, code_verifier = await client.auth_flow_url(
        state=state_uuid,
        redirect_uri=redirect_uri,
        login_hint=login_hint
    )
    conf.pkce_cache.set(state_uuid, {'target_uri': target_uri, 'code_verifier': code_verifier},
                        expire=TTL(FIVE_MINUTES_IN_SECONDS))

    return RedirectResponse(url, status_code=307)


@router.get('/openid_rp/cb')
async def authorization_flow_callback(
        request: Request,
        state: str,
        code: str,
        yw_jwt: str = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    """
        Callback for an ongoing Authorization Code Grant authentification.
        Shall be called by an interactive User Agent after the Identity Provider redirect it.

        Save access token in cookie.
        Also store logged-in user in yw_login_hint (see /openid_rp/login and /openid_rp/auth endpoints).
        Redirect to the target_uri passed to authorization_flow(request, target_uri) − this target_uri is passed
        around in base64 and is in the param state.

    :param yw_jwt:
    :param request:
    :param state:
    :param code:
    :param conf:
    :return:
    """
    cached_state = conf.pkce_cache.get(state)
    if cached_state is None:
        return JSONResponse(status_code=400, content={"invalid param": "Invalid state"})

    oidc_provider = OidcConfig(conf.openid_base_url)
    client = oidc_provider.for_client(conf.openid_client)
    tokens = await client.auth_flow_handle_cb(
        code=code,
        redirect_uri=request.url_for('authorization_flow_callback'),
        code_verifier=(cached_state['code_verifier'])
    )
    session = SessionHandler(
        jwt_cache=conf.jwt_cache,
        session_uuid=(yw_jwt if yw_jwt else str(uuid.uuid4()))
    )
    session.store(tokens)

    decoded_token = await oidc_provider.token_decode(tokens['id_token'])
    username = decoded_token['upn']

    response = RedirectResponse(
        url=(cached_state['target_uri']),
        status_code=307
    )
    response.set_cookie(
        'yw_jwt',
        session.get_uuid(),
        secure=True,
        httponly=True,
        max_age=session.get_remaining_time()
    )
    response.set_cookie(
        'yw_login_hint',
        f"user:{username}",
        secure=True,
        httponly=True,
        expires=ONE_YEAR_IN_SECONDS
    )
    return response


@router.get('/openid_rp/temp_user')
async def login_as_temp_user(
        target_uri: str = '/',
        yw_jwt: str = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    """
        Create a temporary user and get an access token for it.
        Could be call directly or by /openid_rp/login endpoint

        Save access token in cookie.
        Redirect to target_path (can be relative to this endpoint URI)

    :param yw_jwt:
    :param target_uri:
    :param conf:
    :return:
    """
    if conf.admin_client is None:
        return JSONResponse(status_code=403, content={"forbidden": "No administration right on the server side"})

    client_admin = OidcConfig(conf.openid_base_url).for_client(conf.admin_client)

    users_management = KeycloakUsersManagement(conf.keycloak_admin_base_url, client_admin)
    user_name = f"{uuid.uuid4()}@temp.youwol.com"
    password = str(uuid.uuid4())
    await users_management.create_user(user_name, password)

    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    tokens = await client.direct_flow(user_name, password)

    session_uuid = yw_jwt if yw_jwt else str(uuid.uuid4())
    session = SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=session_uuid)
    session.store(tokens)

    response = RedirectResponse(url=target_uri, status_code=307)
    response.set_cookie(
        'yw_jwt',
        session.get_uuid(),
        secure=True,
        httponly=True,
        max_age=session.get_remaining_time()
    )
    return response


@router.get('/openid_rp/logout')
async def logout(
        target_uri: str,
        forget_me: bool = False,
        yw_jwt: Optional[str] = Cookie(default=None),
        yw_jwt_t: Optional[str] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    """
        Logout user.
        Must be call by an interactive User Agent.
        The same rule apply to target_uri as with /openid_rp/auth endpoint

        Delete access token cookie
        Optionally delete yw_login_hint, if forget_me param is true
        Redirect to Identity Provider for logout, which will ultimately redirect to target_uri.

    :param yw_jwt_t:
    :param yw_jwt:
    :param target_uri:
    :param forget_me:
    :param conf:
    :return:
    """
    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    url = await client.logout_url(target_uri)

    session = SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=yw_jwt)
    session.delete()

    if yw_jwt_t:
        real_session = SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=yw_jwt_t)
        real_session.delete()

    response = RedirectResponse(url=url, status_code=307)
    response.set_cookie('yw_jwt', 'DELETED', secure=True, httponly=True, expires=0)
    if forget_me:
        response.set_cookie('yw_login_hint', 'DELETED', secure=True, httponly=True, expires=0)
    if yw_jwt_t:
        response.set_cookie('yw_jwt_t', 'DELETED', secure=True, httponly=True, expires=0)
    return response


@router.get('/openid_rp/login')
async def login(
        request: Request,
        target_uri: str,
        flow: str = 'auto',
        yw_jwt: Optional[str] = Cookie(default=None),
        yw_login_hint: Optional[str] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
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

    :param yw_jwt:
    :param request:
    :param target_uri:
    :param flow:
    :param yw_login_hint:
    :param conf:
    :return:
    """
    if flow == 'auto':
        flow = 'user' if (yw_login_hint or conf.admin_client is None) else 'temp'

    if flow == 'user':
        return await authorization_flow(request, target_uri, yw_login_hint, conf)

    if flow == 'temp':
        return await login_as_temp_user(target_uri, yw_jwt, conf)
