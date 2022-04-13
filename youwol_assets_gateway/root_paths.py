from typing import Optional

from fastapi import APIRouter, Depends
from starlette.requests import Request

from youwol_utils import (
    User, user_info, get_all_individual_groups, Group, private_group_id, to_group_id,
    GroupsResponse,
)
from youwol_utils.context import Context
from youwol_assets_gateway.configurations import get_configuration
from youwol_assets_gateway.routers_deprecated import tree, assets, raw, cdn, misc
from youwol_assets_gateway.routers import stories_backend, cdn_backend, files_backend

router = APIRouter()

router.include_router(
    tree.router,
    prefix="/tree",
    dependencies=[Depends(get_configuration)],
    tags=["tree"]
)

router.include_router(
    assets.router,
    prefix="/assets",
    dependencies=[Depends(get_configuration)],
    tags=["assets"]
)

router.include_router(
    raw.router,
    prefix="/raw",
    dependencies=[Depends(get_configuration)],
    tags=["raw"]
)

router.include_router(
    cdn.router,
    prefix="/cdn",
    dependencies=[Depends(get_configuration)],
    tags=["cdn"]
)

router.include_router(
    misc.router,
    prefix="/misc",
    dependencies=[Depends(get_configuration)],
    tags=["misc"]
)

router.include_router(
    cdn_backend.router,
    prefix="/cdn-backend",
    dependencies=[Depends(get_configuration)],
    tags=["cdn"]
)

router.include_router(
    stories_backend.router,
    prefix="/stories-backend",
    dependencies=[Depends(get_configuration)],
    tags=["cdn"]
)


router.include_router(
    files_backend.router,
    prefix="/files-backend",
    dependencies=[Depends(get_configuration)],
    tags=["files"]
)


@router.get("/healthz")
async def healthz():
    return {"status": "assets-gateway ok"}


@router.get("/user-info",
            response_model=User,
            summary="retrieve user info"
            )
async def get_user_info(request: Request):
    response = Optional[User]
    async with Context.start_ep(
            request=request,
            response=lambda: response,
            action='get user info'
    ):
        user = user_info(request)
        groups = get_all_individual_groups(user["memberof"])
        groups = [Group(id=private_group_id(user), path="private")] + \
                 [Group(id=str(to_group_id(g)), path=g) for g in groups if g]

        response = User(name=user['preferred_username'], groups=groups)
        return response


@router.get("/groups",
            response_model=GroupsResponse,
            summary="list subscribed groups")
async def get_groups(request: Request):
    response = Optional[GroupsResponse]
    async with Context.start_ep(
            request=request,
            response=lambda: response,
            action='get user groups'
    ):
        user = user_info(request)
        groups = get_all_individual_groups(user["memberof"])
        groups = [Group(id=private_group_id(user), path="private")] + [Group(id=str(to_group_id(g)), path=g)
                                                                       for g in groups if g]
        response = GroupsResponse(groups=groups)
        return response
