import base64
import uuid
from typing import Union, Optional, List

from fastapi import APIRouter, Depends
from fastapi.params import Cookie
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from youwol_accounts_backend import Configuration
from youwol_accounts_backend.configuration import get_configuration
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.clients.oidc.users_management import KeycloakUsersManagement

router = APIRouter(tags=['accounts'])


@router.get('/healthz')
async def root():
    return Response(status_code=200, content='{"status":"accounts backend ok"}')


class AccountDetailsUserInfo(BaseModel):
    sub: str
    temp: bool = False
    name: str = "temporary user"
    memberof: List[str]


class AccountDetails(BaseModel):
    userInfo: AccountDetailsUserInfo
    login_hint: Optional[str]


@router.get('/current', response_model=AccountDetails)
async def get_account_details(
        request: Request,
        yw_login_hint: Union[str, None] = Cookie(default=None)
):
    details = AccountDetails(userInfo=AccountDetailsUserInfo.parse_obj(request.state.user_info),
                             login_hint=yw_login_hint)
    return details


@router.get('/openid_rp/auth')
async def authorization_flow(
        request: Request,
        target_path: str = "/",
        yw_login_hint: Union[str, None] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    state = base64.b64encode(target_path.encode('ascii')).decode('ascii')
    redirect_uri = request.url_for('authorization_flow_callback')
    login_hint = None
    if yw_login_hint and yw_login_hint[:5] == 'user:':
        login_hint = yw_login_hint[5:]

    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    url = await client.auth_flow_url(state=state, redirect_uri=redirect_uri, login_hint=login_hint)

    return RedirectResponse(url, status_code=307)


@router.get('/openid_rp/cb')
async def authorization_flow_callback(
        request: Request,
        state: str,
        code: str,
        conf: Configuration = Depends(get_configuration)
):
    target_path = base64.b64decode(state).decode('ascii')
    print(f"Target uri = {target_path}")
    oidc_provider = OidcConfig(conf.openid_base_url)
    client = oidc_provider.for_client(conf.openid_client)
    tokens = await client.auth_flow_handle_cb(code=code, redirect_uri=request.url_for('authorization_flow_callback'))
    decoded_token = await oidc_provider.token_decode(tokens['id_token'])
    response = RedirectResponse(url=target_path, status_code=307)
    response.set_cookie('yw_jwt', tokens['access_token'], secure=True, httponly=True, max_age=tokens['expires_in'])
    response.set_cookie('yw_jwt_r',
                        tokens['refresh_token'],
                        secure=True,
                        httponly=True,
                        max_age=tokens['refresh_expires_in'])
    response.set_cookie('yw_login_hint', f"user:{decoded_token['email']}", secure=True, httponly=True)
    return response


@router.get('/openid_rp/temp_user')
async def login_as_temp_user(target_path: str = '/', conf: Configuration = Depends(get_configuration)):
    if conf.admin_client is None:
        Response(status_code=403, content="No administration right")
    client_admin = OidcConfig(conf.openid_base_url).for_client(conf.admin_client)

    users_management = KeycloakUsersManagement(conf.keycloak_admin_base_url, client_admin)
    user_name = f"{uuid.uuid4()}@temp.youwol.com"
    password = str(uuid.uuid4())
    await users_management.create_user(user_name, password)

    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    tokens = await client.direct_flow(user_name, password)

    response = RedirectResponse(url=target_path, status_code=307)
    response.set_cookie('yw_jwt', tokens['access_token'], secure=True, httponly=True, max_age=tokens['expires_in'])
    response.set_cookie('yw_jwt_r',
                        tokens['refresh_token'],
                        secure=True,
                        httponly=True,
                        max_age=tokens['refresh_expires_in'])
    return response


@router.get('/logout')
async def logout(
        target_path: Optional[str],
        forget_me: bool = False,
        conf: Configuration = Depends(get_configuration)
):
    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    url = await client.logout_url(target_path)
    response = RedirectResponse(url=url, status_code=307)
    response.set_cookie('yw_jwt', 'DELETED', secure=True, httponly=True, expires=0)
    response.set_cookie('yw_jwt_r', 'DELETED', secure=True, httponly=True, expires=0)
    if forget_me:
        response.set_cookie('yw_login_hint', 'DELETED', secure=True, httponly=True, expires=0)
    return response


@router.get('/openid_rp/login')
async def login(
        request: Request,
        target_path: str = '/',
        flow: str = 'auto',
        yw_login_hint: Union[str, None] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    if flow == 'auto':
        flow = 'user' if yw_login_hint else 'temp'

    if flow == 'user':
        return await authorization_flow(request, target_path, yw_login_hint, conf)

    if flow == 'temp':
        return await login_as_temp_user(target_path, conf)


@router.get('/{user_id}/impersonate')
async def impersonate(
        user_id: str,
        yw_jwt: Optional[str] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    tokens = await client.token_exchange(user_id, yw_jwt)

    response = RedirectResponse(url="/", status_code=307)
    response.set_cookie('yw_jwt', tokens['access_token'], secure=True, httponly=True, max_age=tokens['expires_in'])
    response.set_cookie('yw_jwt_r', 'DELETED', secure=True, httponly=True, expires=0)
    return response
