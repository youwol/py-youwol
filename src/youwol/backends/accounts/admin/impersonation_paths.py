# standard library
import uuid

# typing
from typing import Any, Optional

# third parties
from fastapi import Depends
from fastapi.params import Cookie
from pydantic import BaseModel
from starlette.responses import JSONResponse, Response

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.clients.oidc.tokens import restore_tokens, save_tokens

# relative
from ..configuration import Configuration, get_configuration
from ..root_paths import router


class ImpersonationDetails(BaseModel):
    userId: str
    hidden: bool = False


@router.put("/impersonation")
async def start_impersonate(
    details: ImpersonationDetails,
    yw_jwt: Optional[str] = Cookie(default=None),
    yw_jwt_t: Any = Cookie(default=None),
    conf: Configuration = Depends(get_configuration),
):
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

    if conf.admin_client is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    if yw_jwt_t:
        return JSONResponse(
            status_code=400, content={"invalid request": "Already impersonating"}
        )

    response = Response(status_code=201)

    client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    real_tokens = restore_tokens(
        tokens_id=yw_jwt,
        cache=conf.auth_cache,
        oidc_client=client,
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

    admin_client = OidcConfig(conf.openid_base_url).for_client(conf.admin_client)
    impersonation_tokens_data = await admin_client.token_exchange(
        details.userId, real_tokens.access_token()
    )

    impersonation_tokens_id = yw_jwt if details.hidden else str(uuid.uuid4())
    impersonation_tokens = await save_tokens(
        **impersonation_tokens_data,
        cache=conf.auth_cache,
        oidc_client=client,
        tokens_id=impersonation_tokens_id,
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
    yw_jwt: Optional[str] = Cookie(default=None),
    yw_jwt_t: Optional[str] = Cookie(default=None),
    conf: Configuration = Depends(get_configuration),
):
    if conf.admin_client is None:
        return JSONResponse(
            status_code=403,
            content={"forbidden": "no administration right on the server side"},
        )

    if yw_jwt_t is None:
        return JSONResponse(
            status_code=400, content={"invalid request": "Not impersonating"}
        )

    impersonation_tokens = restore_tokens(
        tokens_id=yw_jwt,
        cache=conf.auth_cache,
        oidc_client=OidcConfig(conf.openid_base_url).for_client(conf.openid_client),
    )
    await impersonation_tokens.delete()
    real_tokens = restore_tokens(
        tokens_id=yw_jwt_t,
        cache=conf.auth_cache,
        oidc_client=OidcConfig(conf.openid_base_url).for_client(conf.openid_client),
    )
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
