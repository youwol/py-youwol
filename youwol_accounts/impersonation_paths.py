import uuid
from typing import Optional, Any

from fastapi import Depends
from fastapi.params import Cookie
from pydantic import BaseModel
from starlette.responses import Response, JSONResponse

from youwol_accounts.configuration import Configuration, get_configuration
from youwol_accounts.root_paths import router
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.session_handler import SessionHandler


class ImpersonationDetails(BaseModel):
    userId: str
    hidden: bool = False


@router.put('/impersonation')
async def start_impersonate(
        details: ImpersonationDetails,
        yw_jwt: Optional[str] = Cookie(default=None),
        yw_jwt_t: Any = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
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
        return JSONResponse(status_code=403, content={"forbidden": "no administration right on the server side"})

    if yw_jwt_t:
        return JSONResponse(status_code=400, content={"invalid request": "Already impersonating"})

    response = Response(status_code=201)

    real_session = SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=yw_jwt)
    if details.hidden:
        real_session.delete()
    else:
        response.set_cookie(
            'yw_jwt_t',
            real_session.get_uuid(),
            secure=True,
            httponly=True,
            max_age=real_session.get_remaining_time()
        )

    admin_client = OidcConfig(conf.openid_base_url).for_client(conf.admin_client)
    tokens = await admin_client.token_exchange(details.userId, real_session.get_access_token())

    session_uuid = yw_jwt if details.hidden else str(uuid.uuid4())
    session = SessionHandler(conf.jwt_cache, session_uuid=session_uuid)
    session.store(tokens)

    response.set_cookie(
        'yw_jwt',
        session.get_uuid(),
        secure=True,
        httponly=True,
        max_age=session.get_remaining_time()
    )
    return response


@router.delete('/impersonation')
async def stop_impersonation(
        yw_jwt: Optional[str] = Cookie(default=None),
        yw_jwt_t: Optional[str] = Cookie(default=None),
        conf: Configuration = Depends(get_configuration)
):
    if conf.admin_client is None:
        return JSONResponse(status_code=403, content={"forbidden": "no administration right on the server side"})

    if yw_jwt_t is None:
        return JSONResponse(status_code=400, content={"invalid request": "Not impersonating"})

    real_session = SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=yw_jwt_t)
    SessionHandler(jwt_cache=conf.jwt_cache, session_uuid=yw_jwt).delete()

    response = Response(status_code=204)
    response.set_cookie(
        'yw_jwt',
        yw_jwt_t,
        secure=True,
        httponly=True,
        max_age=real_session.get_remaining_time()
    )
    response.set_cookie(
        'yw_jwt_t',
        'DELETED',
        secure=True,
        httponly=True,
        expires=0
    )
    return response
