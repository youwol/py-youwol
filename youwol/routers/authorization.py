from typing import Optional

from fastapi import APIRouter, Depends, Form
from starlette.requests import Request

from youwol.routers.environment.router import login as login_env
from youwol.routers.environment.models import LoginBody
from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol.context import Context
from youwol.web_socket import WebSocketsCache

router = APIRouter()


@router.get("/user-info",
            summary="retrieve user info")
async def get_user_info(
        config: YouwolEnvironment = Depends(yw_config)
        ):
    user_info = config.get_user_info()
    return {
        "sub": user_info.id,
        "email_verified": True,
        "name": user_info.name,
        "preferred_username": user_info.name,
        "memberof": user_info.memberOf,
        "email": user_info.email,
        }


@router.post("/login",
             summary="login with as new user")
async def login(
        request: Request,
        username: Optional[str] = Form(None),
        config: YouwolEnvironment = Depends(yw_config)
        ):
    """
    this end point should be defined in the user configuration file as it is usually intended
    to mock some auth service from which we don't know the format of the request
    """
    resp = await login_env(request=request, body=LoginBody(email=username), config=config)
    return {"access_token": f"access_token_{resp.email}"}


@router.get("/keycloak-access-token",
            summary="get keycloak access token of current user")
async def keycloak_token(
        request: Request,
        config: YouwolEnvironment = Depends(yw_config)
        ):
    context = Context(
        request=request,
        config=config,
        web_socket=WebSocketsCache.environment
        )
    token = await config.get_auth_token(context)
    return {"access_token": token}
