# typing
from typing import Annotated, Union

# third parties
from fastapi import Depends
from fastapi.params import Cookie
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

# Youwol utilities
from youwol.utils.clients.oidc.service_account_client import UnexpectedResponseStatus

# relative
from ..configuration import Configuration, get_configuration
from ..root_paths import router
from ..utils import url_for

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60


class RegistrationDetails(BaseModel):
    email: str
    target_uri: str


@router.put("/registration")
async def register_from_temp_user(
    request: Request,
    details: RegistrationDetails,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    if conf.keycloak_users_management is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    if "temp" not in request.state.user_info:
        return JSONResponse(
            status_code=400, content={"invalid request": "not a temporary user"}
        )

    params = {"target_uri": details.target_uri}
    redirect_uri = url_for(
        request=request,
        function_name="registration_finalizer",
        https=conf.https,
        **params,
    )

    try:
        await conf.keycloak_users_management.register_user(
            sub=request.state.user_info["sub"],
            email=details.email,
            client_id=conf.oidc_client.client_id(),
            target_uri=redirect_uri,
        )
    except UnexpectedResponseStatus as e:
        return JSONResponse(status_code=e.actual, content=e.content)

    return Response(status_code=202)


@router.get("/registration")
async def registration_finalizer(
    target_uri: str,
    yw_jwt: Annotated[Union[str, None], Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    if conf.keycloak_users_management is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    if yw_jwt is None:
        return JSONResponse(status_code=403, content="no cookie")

    tokens = await conf.tokens_manager.restore_tokens(
        tokens_id=yw_jwt,
    )

    if tokens is None:
        return JSONResponse(
            status_code=400, content={"invalid state": "no tokens found"}
        )

    try:
        await conf.keycloak_users_management.finalize_user(sub=await tokens.sub())
    except UnexpectedResponseStatus as e:
        return JSONResponse(status_code=e.actual, content=e.content)

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
