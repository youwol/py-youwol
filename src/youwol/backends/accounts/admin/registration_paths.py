# typing

# third parties
from fastapi import Depends
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Youwol utilities
from youwol.utils.clients.oidc.service_account_client import UnexpectedResponseStatus
from youwol.utils.servers.request import get_real_client_ip

# relative
from ..configuration import Configuration, get_configuration
from ..root_paths import router
from ..utils import url_for

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60


class RegistrationDetails(BaseModel):
    email: str
    target_uri: str | None = None


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

    redirect_uri = url_for(
        request=request,
        function_name="authorization_flow",
        https=conf.https,
    )

    try:
        await conf.keycloak_users_management.register_user(
            sub=request.state.user_info["sub"],
            email=details.email,
            client_id=conf.oidc_client.client_id(),
            target_uri=redirect_uri,
            ip=get_real_client_ip(request),
        )
    except UnexpectedResponseStatus as e:
        return JSONResponse(status_code=e.actual, content=e.content)

    response = Response(status_code=202)
    response.set_cookie(
        "yw_login_hint",
        f"user:{details.email}",
        secure=True,
        httponly=True,
        max_age=ONE_YEAR_IN_SECONDS,
    )
    return response
