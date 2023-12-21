# typing
from typing import Annotated, Any, Optional

# third parties
from fastapi import APIRouter, Depends
from fastapi.params import Cookie
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Youwol backends
from youwol.backends.accounts.configuration import Configuration, get_configuration

# Youwol utilities
from youwol.utils import get_all_individual_groups, private_group_id, to_group_id

# relative
from .utils import url_for

router = APIRouter(tags=["accounts"])


@router.get("/healthz")
async def root() -> Response:
    return JSONResponse(status_code=200, content={"status": "accounts backend ok"})


class SessionDetailsUserGroup(BaseModel):
    id: str
    path: str


class SessionDetailsUserInfo(BaseModel):
    name: str = "temporary user"
    temp: bool = False
    groups: list[SessionDetailsUserGroup]


class SessionDetails(BaseModel):
    userInfo: SessionDetailsUserInfo
    logoutUrl: str
    accountManagerUrl: str
    remembered: bool


class SessionImpersonationDetails(SessionDetails):
    realUserInfo: SessionDetailsUserInfo


def user_info_from_json(json: Any) -> SessionDetailsUserInfo:
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
    yw_jwt_t: Annotated[Optional[str], Cookie()] = None,
    yw_login_hint: Annotated[Optional[str], Cookie()] = None,
    conf: Configuration = Depends(get_configuration),
) -> SessionDetails:
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

    real_user_info = None

    logout_url = (
        conf.logout_url
        if conf.logout_url
        else url_for(request=request, function_name="logout", https=conf.https)
    )

    account_manager_url = (
        conf.account_manager_url
        if conf.account_manager_url
        else f"{conf.oidc_client.get_base_url()}/account/"
    )

    if yw_jwt_t:
        impersonating_tokens = await conf.tokens_manager.restore_tokens(yw_jwt_t)
        if impersonating_tokens is not None:
            access_token = await impersonating_tokens.access_token()
            real_user_info = user_info_from_json(access_token)

    if real_user_info is not None:
        return SessionImpersonationDetails(
            userInfo=user_info,
            realUserInfo=real_user_info,
            remembered=yw_login_hint is not None,
            logoutUrl=logout_url,
            accountManagerUrl=account_manager_url,
        )

    return SessionDetails(
        userInfo=user_info,
        remembered=yw_login_hint is not None,
        logoutUrl=logout_url,
        accountManagerUrl=account_manager_url,
    )
