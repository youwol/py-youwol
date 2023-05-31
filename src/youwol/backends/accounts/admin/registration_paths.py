# typing
from typing import Optional

# third parties
from fastapi import Cookie, Depends
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.clients.oidc.tokens import restore_tokens
from youwol.utils.clients.oidc.users_management import KeycloakUsersManagement

# relative
from ..configuration import Configuration, get_configuration
from ..root_paths import router

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60


class RegistrationDetails(BaseModel):
    email: str
    target_uri: str


@router.put("/registration")
async def register_from_temp_user(
    request: Request,
    details: RegistrationDetails,
    yw_jwt: Optional[str] = Cookie(default=None),
    conf: Configuration = Depends(get_configuration),
):
    if conf.admin_client is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    if "temp" not in request.state.user_info:
        return JSONResponse(
            status_code=400, content={"invalid request": "not a temporary user"}
        )

    params = {"target_uri": details.target_uri, "session_id": yw_jwt}
    redirect_uri = request.url_for("registration_finalizer").include_query_params(
        **params
    )

    client_admin = OidcConfig(conf.openid_base_url).for_client(conf.admin_client)
    users_management = KeycloakUsersManagement(
        conf.keycloak_admin_base_url, client_admin
    )
    try:
        await users_management.register_user(
            sub=(request.state.user_info["sub"]),
            email=details.email,
            client_id=conf.openid_client.client_id,
            target_uri=str(redirect_uri),
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e.args[0])})

    tokens = restore_tokens(
        tokens_id=yw_jwt,
        cache=conf.auth_cache,
        oidc_client=OidcConfig(conf.openid_base_url).for_client(conf.openid_client),
    )

    await tokens.refresh()

    return Response(status_code=202)


@router.get("/registration")
async def registration_finalizer(
    target_uri: str, session_id: str, conf: Configuration = Depends(get_configuration)
):
    if conf.admin_client is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    oidc_config = OidcConfig(conf.openid_base_url)
    client_admin = oidc_config.for_client(conf.admin_client)
    users_management = KeycloakUsersManagement(
        conf.keycloak_admin_base_url, client_admin
    )
    tokens = restore_tokens(
        session_id,
        cache=conf.auth_cache,
        oidc_client=oidc_config.for_client(conf.openid_client),
    )
    await users_management.finalize_user(sub=await tokens.sub())

    await tokens.refresh()

    response = RedirectResponse(target_uri, status_code=307)
    response.set_cookie(
        "yw_jwt",
        tokens.id(),
        secure=True,
        httponly=True,
        max_age=tokens.remaining_time(),
    )
    response.set_cookie(
        "yw_login_hint",
        f"user:{await tokens.username()}",
        secure=True,
        httponly=True,
        max_age=ONE_YEAR_IN_SECONDS,
    )
    return response
