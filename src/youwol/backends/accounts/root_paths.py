# typing
from typing import Any, List, Optional

# third parties
from fastapi import APIRouter, Depends
from fastapi.params import Cookie
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

# Youwol backends
from youwol.backends.accounts.configuration import Configuration, get_configuration

# Youwol utilities
from youwol.utils import (
    OidcConfig,
    get_all_individual_groups,
    private_group_id,
    to_group_id,
)
from youwol.utils.clients.oidc.tokens import restore_tokens

router = APIRouter(tags=["accounts"])


@router.get("/healthz")
async def root():
    return JSONResponse(status_code=200, content={"status": "accounts backend ok"})


class SessionDetailsUserGroup(BaseModel):
    id: str
    path: str


class SessionDetailsUserInfo(BaseModel):
    name: str = "temporary user"
    temp: bool = False
    groups: List[SessionDetailsUserGroup]


class SessionDetails(BaseModel):
    userInfo: SessionDetailsUserInfo
    remembered: bool


class SessionImpersonationDetails(SessionDetails):
    realUserInfo: SessionDetailsUserInfo


def user_info_from_json(json: Any):
    return SessionDetailsUserInfo(
        name=json["name"] if "name" in json else "temporary user",
        temp=json["temp"] if "temp" in json else False,
        groups=[SessionDetailsUserGroup(id=private_group_id(json), path="private")]
        + [
            SessionDetailsUserGroup(id=str(to_group_id(g)), path=g)
            for g in get_all_individual_groups(json["memberof"])
            if g
        ],
    )


@router.get("/session", response_model=SessionDetails)
async def get_session_details(
    request: Request,
    yw_jwt_t: Optional[str] = Cookie(default=None),
    yw_login_hint: Optional[str] = Cookie(default=None),
    conf: Configuration = Depends(get_configuration),
):
    """
        Return the details of the current session, as determined by AuthMiddleware
        Also indicate the login_hint, if any.

    :param request:
    :param yw_jwt_t:
    :param yw_login_hint:
    :param conf:
    :return:
    """

    user_info = user_info_from_json(request.state.user_info)

    oidc_client = OidcConfig(conf.openid_base_url).for_client(conf.openid_client)
    if yw_jwt_t:
        tokens = restore_tokens(
            yw_jwt_t, cache=conf.auth_cache, oidc_client=oidc_client
        )
        access_token = await tokens.access_token()
        real_user_info = user_info_from_json(access_token)
        return SessionImpersonationDetails(
            userInfo=user_info,
            realUserInfo=real_user_info,
            remembered=yw_login_hint is not None,
        )
    else:
        return SessionDetails(userInfo=user_info, remembered=yw_login_hint is not None)
