from typing import Optional

from fastapi import Cookie, Depends
from pydantic import BaseModel
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, RedirectResponse

from youwol_accounts.configuration import Configuration, get_configuration
from youwol_accounts.root_paths import router
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.clients.oidc.users_management import KeycloakUsersManagement
from youwol_utils.session_handler import SessionHandler


class RegistrationDetails(BaseModel):
    email: str
    target_uri: str


@router.put("/registration")
async def register_from_temp_user(
        request: Request,
        details: RegistrationDetails,
        yw_jwt: Optional[str] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    if conf.admin_client is None:
        return JSONResponse(status_code=403, content={"forbidden": "no administration right on the server side"})

    session = SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=yw_jwt)
    if 'temp' not in request.state.user_info:
        return JSONResponse(status_code=400, content={'invalid request': 'not a temporary user'})

    params = {
        'target_uri': details.target_uri,
        'session_id': yw_jwt
    }
    redirect_uri = URL(request.url_for('registration_finalizer')).include_query_params(**params)

    client_admin = OidcConfig(conf.openid_base_url).for_client(conf.admin_client)
    users_management = KeycloakUsersManagement(conf.keycloak_admin_base_url, client_admin)
    try:
        await users_management.register_user(
            sub=(request.state.user_info['sub']),
            email=details.email,
            client_id=conf.openid_client.client_id,
            target_uri=str(redirect_uri)
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e.args[0])})

    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    session.store(await client.refresh(session.get_refresh_token()))

    return Response(status_code=202)


@router.get("/openid_rp/finalize_registration")
async def registration_finalizer(
        target_uri: str,
        session_id: str,
        conf: Configuration = Depends(get_configuration)
):
    if conf.admin_client is None:
        return JSONResponse(status_code=403, content={"forbidden": "no administration right on the server side"})

    session = SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=session_id)

    oidc_config = OidcConfig(conf.openid_base_url)
    client_admin = oidc_config.for_client(conf.admin_client)
    users_management = KeycloakUsersManagement(conf.keycloak_admin_base_url, client_admin)
    token_data = await oidc_config.token_decode(session.get_id_token())
    await users_management.finalize_user(sub=token_data['sub'])

    client = oidc_config.for_client(conf.openid_client)
    session.store(await client.refresh(session.get_refresh_token()))
    id_token_data = await oidc_config.token_decode(session.get_id_token())
    response = RedirectResponse(target_uri, status_code=307)
    response.set_cookie(
        'yw_jwt',
        session.get_uuid(),
        secure=True,
        httponly=True,
        max_age=session.get_remaining_time()
    )
    response.set_cookie(
        'yw_login_hint',
        f"user:{id_token_data['upn']}",
        secure=True,
        httponly=True,
        max_age=session.get_remaining_time()
    )
    return response
