import asyncio
from typing import Optional, Mapping

import aiohttp
from aiohttp import ClientConnectorError
from fastapi import APIRouter, HTTPException, Depends, Form
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response

from youwol.routers.environment.router import login as login_env
from youwol.routers.environment.models import LoginBody
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.context import Context
from youwol.routers.backends.utils import get_all_backends
from youwol.web_socket import WebSocketsCache

import youwol.services.backs.cdn.root_paths as cdn
import youwol.services.backs.treedb.root_paths as treedb
import youwol.services.backs.assets.root_paths as assets
import youwol.services.backs.flux.root_paths as flux
import youwol.services.backs.stories.root_paths as stories
import youwol.services.backs.assets_gateway.root_paths as assets_gateway


router = APIRouter()
cached_headers = None


router.include_router(cdn.router, prefix="/cdn-backend", tags=["cdn"])
router.include_router(treedb.router, prefix="/treedb-backend", tags=["treedb"])
router.include_router(assets.router, prefix="/assets-backend", tags=["assets"])
router.include_router(flux.router, prefix="/flux-backend", tags=["flux"])
router.include_router(stories.router, prefix="/stories-backend", tags=["stories"])
router.include_router(assets_gateway.router, prefix="/assets-gateway", tags=["assets-gateway"])


@router.get("/authorization/user-info",
            summary="retrieve user info")
async def get_user_info(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
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


@router.post("/authorization/login",
             summary="login with as new user")
async def login(
        request: Request,
        username: Optional[str] = Form(None),
        config: YouwolConfiguration = Depends(yw_config)
        ):
    """
    this end point should be defined in the user configuration file as it is usually intended
    to mock some auth service fro which we don't know the format of the request
    """
    resp = await login_env(request=request, body=LoginBody(email=username), config=config)
    return {"access_token": f"access_token_{resp.email}"}


@router.get("/authorization/keycloak-access-token",
            summary="get keycloak access token of current user")
async def keycloak_token(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(
        request=request,
        config=config,
        web_socket=WebSocketsCache.environment
        )
    token = await config.get_auth_token(context)
    return {"access_token": token}

