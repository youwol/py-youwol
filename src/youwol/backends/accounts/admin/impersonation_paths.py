# typing
from typing import Annotated, Optional

# third parties
from fastapi import Depends
from fastapi.params import Cookie
from pydantic import BaseModel
from starlette.responses import JSONResponse, Response

# relative
from ..configuration import (
    Configuration,
    default_tokens_id_generator,
    get_configuration,
)
from ..root_paths import router


class ImpersonationDetails(BaseModel):
    userId: str
    hidden: bool = False


@router.put("/impersonation")
async def start_impersonate(
    details: ImpersonationDetails,
    yw_jwt: Annotated[Optional[str], Cookie()] = None,
    yw_jwt_t: Annotated[Optional[str], Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    """
        Create a new session impersonating user, if current user has the correct role.
        user_id can be the sub or the login name af the user to impersonate

        Save access token in cookie.
        Redirect to the root path.

    :param yw_jwt_t:
    :param details:
    :param yw_jwt:
    :param conf:
    :return:
    """

    if conf.keycloak_admin_client is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    if yw_jwt_t is not None:
        return JSONResponse(
            status_code=400, content={"invalid request": "Already impersonating"}
        )

    if yw_jwt is None:
        return JSONResponse(status_code=403, content="missing cookie")

    response = Response(status_code=201)

    real_tokens = await conf.tokens_manager.restore_tokens(
        tokens_id=yw_jwt,
    )

    if real_tokens is None:
        return JSONResponse(
            status_code=400, content={"invalid request": "No real tokens"}
        )

    if details.hidden:
        await real_tokens.delete()
    else:
        response.set_cookie(
            "yw_jwt_t",
            real_tokens.id(),
            secure=True,
            httponly=True,
            max_age=real_tokens.remaining_time(),
        )

    real_access_token = await real_tokens.access_token()
    impersonation_tokens_data = await conf.keycloak_admin_client.impersonation(
        requested_subject=details.userId, subject_token=real_access_token
    )

    impersonation_tokens = await conf.tokens_manager.save_tokens(
        tokens_id=(yw_jwt if details.hidden else default_tokens_id_generator()),
        tokens_data=impersonation_tokens_data,
    )

    response.set_cookie(
        "yw_jwt",
        impersonation_tokens.id(),
        secure=True,
        httponly=True,
        max_age=impersonation_tokens.remaining_time(),
    )
    return response


@router.delete("/impersonation")
async def stop_impersonation(
    yw_jwt: Annotated[Optional[str], Cookie()] = None,
    yw_jwt_t: Annotated[Optional[str], Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> Response:
    if conf.keycloak_admin_client is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    if yw_jwt_t is None:
        return JSONResponse(
            status_code=400, content={"invalid request": "Not impersonating"}
        )

    if yw_jwt is None:
        return JSONResponse(status_code=403, content="missing cookie")

    impersonation_tokens = await conf.tokens_manager.restore_tokens(
        tokens_id=yw_jwt,
    )

    real_tokens = await conf.tokens_manager.restore_tokens(
        tokens_id=yw_jwt_t,
    )

    if impersonation_tokens is None or real_tokens is None:
        return JSONResponse(
            status_code=400, content={"invalid state": "no tokens found"}
        )

    await impersonation_tokens.delete()
    response = Response(status_code=204)
    response.set_cookie(
        "yw_jwt",
        real_tokens.id(),
        secure=True,
        httponly=True,
        max_age=real_tokens.remaining_time(),
    )
    response.set_cookie("yw_jwt_t", "DELETED", secure=True, httponly=True, expires=0)
    return response
